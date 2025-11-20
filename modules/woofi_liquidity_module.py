import math
from templates.liquidity_module import LiquidityModule, Token
from typing import Dict, Optional
from decimal import Decimal


class WOOFiPoolMath:
    def sell_quote_token_out(
        self,
        pool_state: Dict,
        fixed_parameters: Dict,
        output_token: Token,
        input_amount: int
    ) -> tuple[int | None, int | None]:
        base_token_fee_rate = pool_state["output_token_fee_rate"]
        base_token_max_gamma = pool_state["output_token_max_gamma"]
        base_token_max_notional_swap = pool_state["output_token_max_notional_swap"]

        base_token_price = pool_state["output_token_price"]
        base_token_spread = pool_state["output_token_spread"]
        base_token_coeff = pool_state["output_token_coeff"]
        base_token_wo_feasible = pool_state["output_token_wo_feasible"]
        
        base_token_decimals = output_token.decimals

        swap_fee = int(input_amount * base_token_fee_rate / fixed_parameters["base_fee_rate"])
        quote_token_amount_after_fee = input_amount - swap_fee

        base_token_amount = self.calc_base_token_amount_sell_quote_out(fixed_parameters, quote_token_amount_after_fee, base_token_max_gamma, base_token_max_notional_swap, base_token_price, base_token_spread, base_token_coeff, base_token_wo_feasible, base_token_decimals)
        if base_token_amount is None:
            return None, None

        base_token_reserve = pool_state["output_token_reserve"]
        if base_token_amount > base_token_reserve:
            return None, None
        
        return swap_fee, base_token_amount
    
    def sell_base_token_out(
        self,
        pool_state: Dict,
        fixed_parameters: Dict,
        input_token: Token,
        input_amount: int
    ) -> tuple[int | None, int | None]:
        base_token_fee_rate = pool_state["input_token_fee_rate"]
        base_token_max_gamma = pool_state["input_token_max_gamma"]
        base_token_max_notional_swap = pool_state["input_token_max_notional_swap"]

        base_token_price = pool_state["input_token_price"]
        base_token_spread = pool_state["input_token_spread"]
        base_token_coeff = pool_state["input_token_coeff"]
        base_token_wo_feasible = pool_state["input_token_wo_feasible"]

        base_token_decimals = input_token.decimals

        quote_token_amount = self.calc_quote_token_amount_sell_base_out(fixed_parameters, input_amount, base_token_max_gamma, base_token_max_notional_swap, base_token_price, base_token_spread, base_token_coeff, base_token_wo_feasible, base_token_decimals)
        if quote_token_amount is None:
            return None, None

        quote_token_reserve = pool_state["output_token_reserve"]
        if quote_token_amount > quote_token_reserve:
            return None, None
        
        swap_fee = int(quote_token_amount * base_token_fee_rate / fixed_parameters["base_fee_rate"])
        quote_token_amount_after_fee = quote_token_amount - swap_fee

        return swap_fee, quote_token_amount_after_fee
    
    def swap_base_to_base_out(
        self,
        pool_state: Dict,
        fixed_parameters: Dict,
        input_token: Token,
        output_token: Token,
        input_amount: int
    ) -> tuple[int | None, int | None]:
        base1_token_fee_rate, base2_token_fee_rate = pool_state["input_token_fee_rate"], pool_state["output_token_fee_rate"]
        base1_token_max_gamma, base2_token_max_gamma = pool_state["input_token_max_gamma"], pool_state["output_token_max_gamma"]
        base1_token_max_notional_swap, base2_token_max_notional_swap = pool_state["input_token_max_notional_swap"], pool_state["output_token_max_notional_swap"]

        base1_token_price, base2_token_price = pool_state["input_token_price"], pool_state["output_token_price"]
        base1_token_spread, base2_token_spread = pool_state["input_token_spread"], pool_state["output_token_spread"]
        base1_token_coeff, base2_token_coeff = pool_state["input_token_coeff"], pool_state["output_token_coeff"]
        base1_token_wo_feasible, base2_token_wo_feasible = pool_state["input_token_wo_feasible"], pool_state["output_token_wo_feasible"]

        base1_token_decimals, base2_token_decimals = input_token.decimals, output_token.decimals

        fee_rate = max(base1_token_fee_rate, base2_token_fee_rate)
        spread = max(base1_token_spread, base2_token_spread)

        quote_token_amount = self.calc_quote_token_amount_sell_base_out(fixed_parameters, input_amount, base1_token_max_gamma, base1_token_max_notional_swap, base1_token_price, spread, base1_token_coeff, base1_token_wo_feasible, base1_token_decimals)
        if quote_token_amount is None:
            return None, None

        swap_fee = int(quote_token_amount * fee_rate / fixed_parameters["base_fee_rate"])
        if swap_fee > pool_state["quote_token_reserve"]:
            return None, None
        
        quote_token_amount_after_fee = quote_token_amount - swap_fee
        base2_token_amount = self.calc_base_token_amount_sell_quote_out(
            fixed_parameters, quote_token_amount_after_fee, base2_token_max_gamma, base2_token_max_notional_swap, base2_token_price, spread, base2_token_coeff, base2_token_wo_feasible, base2_token_decimals
        )
        if base2_token_amount is None:
            return None, None

        base2_token_reserve = pool_state["output_token_reserve"]
        if base2_token_amount > base2_token_reserve:
            return None, None
        
        return swap_fee, base2_token_amount
    
    def calc_base_token_amount_sell_quote_out(
        self,
        fixed_parameters: Dict,
        quote_token_amount_after_fee: int,
        base_token_max_gamma: int,
        base_token_max_notional_swap: int,
        base_token_price: int,
        base_token_spread: int,
        base_token_coeff: int,
        base_token_wo_feasible: bool,
        base_token_decimals: int
    ) -> int | None:
        if not base_token_wo_feasible:
            return None
        
        if base_token_price <= 0:
            return None
        
        if quote_token_amount_after_fee > base_token_max_notional_swap:
            return None
        
        gamma = quote_token_amount_after_fee * base_token_coeff // (10 ** fixed_parameters["quote_token_decimals"])
        if gamma > base_token_max_gamma:
            return None
        
        baes_amount = int(((
            (quote_token_amount_after_fee * (10 ** base_token_decimals) * (10 ** fixed_parameters["oracle_price_decimals"])) // base_token_price
        ) * (1e18 - gamma - base_token_spread)) // 1e18 // (10 ** fixed_parameters["quote_token_decimals"]))

        return baes_amount
    
    def calc_quote_token_amount_sell_base_out(
        self,
        fixed_parameters: Dict,
        base_token_amount: int,
        base_token_max_gamma: int,
        base_token_max_notional_swap: int,
        base_token_price: int,
        base_token_spread: int,
        base_token_coeff: int,
        base_token_wo_feasible: bool,
        base_token_decimals: int
    ) -> int | None:
        if not base_token_wo_feasible:
            return None
        
        if base_token_price <= 0:
            return None
        
        notional_swap = (base_token_amount * base_token_price * (10 ** fixed_parameters["quote_token_decimals"])) / (10 ** base_token_decimals) / (10 ** fixed_parameters["oracle_price_decimals"])
        if notional_swap > base_token_max_notional_swap:
            return None
        
        gamma = (base_token_amount * base_token_price * base_token_coeff) // (10 ** fixed_parameters["oracle_price_decimals"]) // (10 ** base_token_decimals)
        if gamma > base_token_max_gamma:
            return None
        
        quote_token_amount = int(
            (
                (base_token_amount * base_token_price * (10 ** fixed_parameters["quote_token_decimals"])) // (10 ** fixed_parameters["oracle_price_decimals"]) * (1e18 - gamma - base_token_spread)
            ) // 1e18 // (10 ** base_token_decimals)
        )

        return quote_token_amount
    
    def sell_quote_token_in(
        self,
        pool_state: Dict,
        fixed_parameters: Dict,
        output_token: Token,
        output_amount: int
    ) -> tuple[int | None, int | None]:
        base_token_reserve = pool_state["output_token_reserve"]
        if output_amount > base_token_reserve:
            return None, None
        
        base_token_fee_rate = pool_state["output_token_fee_rate"]
        base_token_max_gamma = pool_state["output_token_max_gamma"]
        base_token_max_notional_swap = pool_state["output_token_max_notional_swap"]

        base_token_price = pool_state["output_token_price"]
        base_token_spread = pool_state["output_token_spread"]
        base_token_coeff = pool_state["output_token_coeff"]
        base_token_wo_feasible = pool_state["output_token_wo_feasible"]

        base_token_decimals = output_token.decimals

        quote_token_amount_after_fee = self.calc_base_token_amount_sell_quote_in(fixed_parameters, output_amount, base_token_max_gamma, base_token_max_notional_swap, base_token_price, base_token_spread, base_token_coeff, base_token_wo_feasible, base_token_decimals)
        if quote_token_amount_after_fee is None:
            return None, None

        quote_token_amount = quote_token_amount_after_fee * fixed_parameters["base_fee_rate"] / (fixed_parameters["base_fee_rate"] - base_token_fee_rate)
        swap_fee = quote_token_amount - quote_token_amount_after_fee

        return swap_fee, quote_token_amount

    def sell_base_token_in(
        self,
        pool_state: Dict,
        fixed_parameters: Dict,
        input_token: Token,
        output_amount: int
    ) -> tuple[int | None, int | None]:
        base_token_fee_rate = pool_state["input_token_fee_rate"]
        base_token_max_gamma = pool_state["input_token_max_gamma"]
        base_token_max_notional_swap = pool_state["input_token_max_notional_swap"]

        base_token_price = pool_state["input_token_price"]
        base_token_spread = pool_state["input_token_spread"]
        base_token_coeff = pool_state["input_token_coeff"]
        base_token_wo_feasible = pool_state["input_token_wo_feasible"]

        base_token_decimals = input_token.decimals

        quote_token_amount = output_amount * fixed_parameters["base_fee_rate"] / (fixed_parameters["base_fee_rate"] - base_token_fee_rate)
        quote_token_reserve = pool_state["output_token_reserve"]
        if quote_token_amount > quote_token_reserve:
            return None, None
        
        swap_fee = quote_token_amount - output_amount

        base_token_amount = self.calc_quote_token_amount_sell_base_in(fixed_parameters, quote_token_amount, base_token_max_gamma, base_token_max_notional_swap, base_token_price, base_token_spread, base_token_coeff, base_token_wo_feasible, base_token_decimals)
        if base_token_amount is None:
            return None, None

        return swap_fee, base_token_amount

    def swap_base_to_base_in(
        self,
        pool_state: Dict,
        fixed_parameters: Dict,
        input_token: Token,
        output_token: Token,
        output_amount: int
    ):
        base2_token_reserve = pool_state["output_token_reserve"]
        if output_amount > base2_token_reserve:
            return None, None
        
        base1_token_fee_rate, base2_token_fee_rate = pool_state["input_token_fee_rate"], pool_state["output_token_fee_rate"]
        base1_token_max_gamma, base2_token_max_gamma = pool_state["input_token_max_gamma"], pool_state["output_token_max_gamma"]
        base1_token_max_notional_swap, base2_token_max_notional_swap = pool_state["input_token_max_notional_swap"], pool_state["output_token_max_notional_swap"]

        base1_token_price, base2_token_price = pool_state["input_token_price"], pool_state["output_token_price"]
        base1_token_spread, base2_token_spread = pool_state["input_token_spread"], pool_state["output_token_spread"]
        base1_token_coeff, base2_token_coeff = pool_state["input_token_coeff"], pool_state["output_token_coeff"]
        base1_token_wo_feasible, base2_token_wo_feasible = pool_state["input_token_wo_feasible"], pool_state["output_token_wo_feasible"]

        base1_token_decimals, base2_token_decimals = input_token.decimals, output_token.decimals

        fee_rate = max(base1_token_fee_rate, base2_token_fee_rate)
        spread = max(base1_token_spread, base2_token_spread)

        quote_token_amount_after_fee = self.calc_base_token_amount_sell_quote_in(fixed_parameters, output_amount, base2_token_max_gamma, base2_token_max_notional_swap, base2_token_price, spread, base2_token_coeff, base2_token_wo_feasible, base2_token_decimals)
        if quote_token_amount_after_fee is None:
            return None, None
        
        quote_token_amount = quote_token_amount_after_fee * fixed_parameters["base_fee_rate"] / (fixed_parameters["base_fee_rate"] - fee_rate)
        swap_fee = quote_token_amount - quote_token_amount_after_fee
        if swap_fee > pool_state["quote_token_reserve"]:
            return None, None
        
        base1_token_amount = self.calc_quote_token_amount_sell_base_in(fixed_parameters, quote_token_amount, base1_token_max_gamma, base1_token_max_notional_swap, base1_token_price, spread, base1_token_coeff, base1_token_wo_feasible, base1_token_decimals)
        if base1_token_amount is None:
            return None, None

        return swap_fee, base1_token_amount
    
    def calc_base_token_amount_sell_quote_in(
        self,
        fixed_parameters: Dict,
        base_token_amount: int,
        base_token_max_gamma: int,
        base_token_max_notional_swap: int,
        base_token_price: int,
        base_token_spread: int,
        base_token_coeff: int,
        base_token_wo_feasible: bool,
        base_token_decimals: int
    ) -> int | None:
        if not base_token_wo_feasible:
            return None
        
        if base_token_price <= 0:
            return None
        
        qd = 10 ** fixed_parameters["quote_token_decimals"]
        pd = 10 ** fixed_parameters["oracle_price_decimals"]
        bd = 10 ** base_token_decimals
        
        a = 1e36 * bd * pd * base_token_coeff // base_token_price // 1e18 // (qd ** 2)
        b = 1e36 * bd * pd * (base_token_spread - 1e18) // base_token_price // qd // 1e18
        c = 1e36 * base_token_amount

        delta = b ** 2 - 4 * a * c
        if delta < 0:
            return None
        
        x1 = (-1 * b + math.sqrt(delta)) // (2 * a)
        x2 = (-1 * b - math.sqrt(delta)) // (2 * a)

        notional_value_with_qd = base_token_price * base_token_amount * qd // pd // bd
        if abs(x1 - notional_value_with_qd) < abs(x2 - notional_value_with_qd):
            quote_token_amount_after_fee = int(x1)
        else:
            quote_token_amount_after_fee = int(x2)
        
        if quote_token_amount_after_fee < 0:
            return None
        
        if quote_token_amount_after_fee > base_token_max_notional_swap:
            return None
        
        gamma = quote_token_amount_after_fee * base_token_coeff // qd
        if gamma > base_token_max_gamma:
            return None
        
        return quote_token_amount_after_fee
    
    def calc_quote_token_amount_sell_base_in(
        self,
        fixed_parameters: Dict,
        quote_token_amount: int,
        base_token_max_gamma: int,
        base_token_max_notional_swap: int,
        base_token_price: int,
        base_token_spread: int,
        base_token_coeff: int,
        base_token_wo_feasible: bool,
        base_token_decimals: int
    ) -> int | None:
        if not base_token_wo_feasible:
            return None
        
        if base_token_price <= 0:
            return None
        
        qd = 10 ** fixed_parameters["quote_token_decimals"]
        pd = 10 ** fixed_parameters["oracle_price_decimals"]
        bd = 10 ** base_token_decimals

        a = 1e36 * (base_token_price ** 2) * qd * base_token_coeff // (pd ** 2) // bd
        b = 1e36 * base_token_price * qd * (base_token_spread - 1e18) // pd
        c = 1e36 * quote_token_amount * 1e18 * bd

        delta = b ** 2 - 4 * a * c
        if delta < 0:
            return None
        
        x1 = (-1 * b + math.sqrt(delta)) // (2 * a)
        x2 = (-1 * b - math.sqrt(delta)) // (2 * a)

        notional_value_with_qd1 = base_token_price * x1 * qd // pd // bd
        notional_value_with_qd2 = base_token_price * x2 * qd // pd // bd

        if abs(notional_value_with_qd1 - quote_token_amount) < abs(notional_value_with_qd2 - quote_token_amount):
            base_token_amount = int(x1)
        else:
            base_token_amount = int(x2)
        
        if base_token_amount < 0:
            return None
        
        notional_swap = base_token_amount * base_token_price * qd // bd // pd
        if notional_swap > base_token_max_notional_swap:
            return None
        
        gamma = base_token_amount * base_token_price * base_token_coeff // pd // bd
        if gamma > base_token_max_gamma:
            return None
        
        return base_token_amount


class WOOFiLiquidityModule(LiquidityModule):
    def get_amount_out(
        self,
        pool_state: Dict,
        fixed_parameters: Dict,
        input_token: Token,
        output_token: Token,
        input_amount: int,
    ) -> tuple[int | None, int | None]:
        # Implement logic to calculate output amount given input amount
        pool_math = WOOFiPoolMath()
        if input_token.address == fixed_parameters["quote_token"].address:
            return pool_math.sell_quote_token_out(pool_state, fixed_parameters, output_token, input_amount)
        elif output_token.address == fixed_parameters["quote_token"].address:
            return pool_math.sell_base_token_out(pool_state, fixed_parameters, input_token, input_amount)
        else:
            return pool_math.swap_base_to_base_out(pool_state, fixed_parameters, input_token, output_token, input_amount)

    def get_amount_in(
        self,
        pool_state: Dict,
        fixed_parameters: Dict,
        input_token: Token,
        output_token: Token,
        output_amount: int
    ) -> tuple[int | None, int | None]:
        # Implement logic to calculate required input amount given output amount
        pool_math = WOOFiPoolMath()
        if input_token.address == fixed_parameters["quote_token"].address:
            return pool_math.sell_quote_token_in(pool_state, fixed_parameters, output_token, output_amount)
        elif output_token.address == fixed_parameters["quote_token"].address:
            return pool_math.sell_base_token_in(pool_state, fixed_parameters, input_token, output_amount)
        else:
            return pool_math.swap_base_to_base_in(pool_state, fixed_parameters, input_token, output_token, output_amount)

    def get_apy(self, pool_state: Dict) -> Decimal:
        # Implement APY calculation logic
        pass

    def get_tvl(self, pool_state: Dict, token: Optional[Token] = None) -> Decimal:
        # Implement TVL calculation logic
        pass
