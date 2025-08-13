from datetime import datetime
from decimal import Decimal
import unittest

from modules.woofi_liquidity_module import WOOFiLiquidityModule
from templates.liquidity_module import Token


class TestWOOFiLiquidityModule(unittest.TestCase):
    def setUp(self):
        self.module = WOOFiLiquidityModule()
        self.now = int(datetime.now().timestamp())
        self.input_token = Token(address="0x4200000000000000000000000000000000000006", decimals=18, symbol="WETH", reference_price=Decimal(1_750))
        self.output_token = Token(address="0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf", decimals=8, symbol="cbBTC", reference_price=Decimal(92_000))
        
        self.valid_pool_state = {
            "input_token_reserve": 100000000000000000000,
            "input_token_fee_rate": 25,
            "input_token_max_gamma": 3000000000000000,
            "input_token_max_notional_swap": 1000000000000,
            "input_token_price": 175000000000,
            "input_token_spread": 941000000000000,
            "input_token_coeff": 1660000000,
            "input_token_wo_feasible": True,
            "output_token_reserve": 10000000000,
            "output_token_fee_rate": 25,
            "output_token_max_gamma": 3000000000000000,
            "output_token_max_notional_swap": 1000000000000,
            "output_token_price": 9200000000000,
            "output_token_spread": 1050000000000000,
            "output_token_coeff": 1660000000,
            "output_token_wo_feasible": True,
            "quote_token_reserve": 1000000000,
        }

        self.fixed_parameters = {
            "base_fee_rate": int(1e5),
            "quote_token_decimals": 6,
            "oracle_price_decimals": 8,
            "quote_token": Token(address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", decimals=6, symbol="USDC", reference_price=Decimal(1)),
        }

    def test_get_amount_out(self):
        input_amount = int(10e18)
        _, amount_out = self.module.get_amount_out(self.valid_pool_state, self.fixed_parameters, self.input_token, self.output_token, input_amount)
        self.assertIsNotNone(amount_out)
        self.assertEqual(amount_out, 18_975_966)


    def test_get_amount_in(self):
        output_amount = int(1e8)
        _, amount_in = self.module.get_amount_in(self.valid_pool_state, self.fixed_parameters, self.input_token, self.output_token, output_amount)
        self.assertIsNotNone(amount_in)
        self.assertEqual(amount_in, 52_711_323_471_118_491_648)


if __name__ == "__main__":
    unittest.main()
