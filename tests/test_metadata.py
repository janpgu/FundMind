import pytest
import respx
import httpx

from fund_mind import Config, fetch_fund_metadata

ISIN = "CH0002788708"
CONFIG = Config()
METADATA_URL = CONFIG.fund_data_url


def full_payload():
    return {
        "Data": {
            "S": {
                "OFST160100": "SICAV",
                "OFST452100": "0.0182",
                "OFEP010100": "252",
                "OFEP040400": "Growth objective",
                "OFST001020": "UBS Fund Management",
                "OFST010010": "CH",
                "OFST010240": "1988-11-28",
                "OFST010410": "USD",
            }
        }
    }


@pytest.mark.asyncio
class TestFetchFundMetadata:
    async def test_all_fields_extracted(self):
        with respx.mock:
            respx.get(METADATA_URL).mock(return_value=httpx.Response(200, json=full_payload()))
            async with httpx.AsyncClient(cookies=CONFIG.cookies) as client:
                result = await fetch_fund_metadata(client, ISIN, CONFIG)
        assert result["legal_form"] == "SICAV"
        assert result["ter_excl_performance_fee"] == "0.0182"
        assert result["ept_valuation_frequency"] == "252"
        assert result["ept_investment_objective"] == "Growth objective"
        assert result["manco"] == "UBS Fund Management"
        assert result["fund_domicile"] == "CH"
        assert result["fund_launch_date"] == "1988-11-28"
        assert result["fund_currency"] == "USD"

    async def test_null_field_returns_empty_string(self):
        payload = full_payload()
        payload["Data"]["S"]["OFST160100"] = None
        with respx.mock:
            respx.get(METADATA_URL).mock(return_value=httpx.Response(200, json=payload))
            async with httpx.AsyncClient(cookies=CONFIG.cookies) as client:
                result = await fetch_fund_metadata(client, ISIN, CONFIG)
        assert result["legal_form"] == ""

    async def test_missing_field_returns_empty_string(self):
        payload = full_payload()
        del payload["Data"]["S"]["OFST010410"]
        with respx.mock:
            respx.get(METADATA_URL).mock(return_value=httpx.Response(200, json=payload))
            async with httpx.AsyncClient(cookies=CONFIG.cookies) as client:
                result = await fetch_fund_metadata(client, ISIN, CONFIG)
        assert result["fund_currency"] == ""

    async def test_http_error_returns_empty_dict(self):
        with respx.mock:
            respx.get(METADATA_URL).mock(return_value=httpx.Response(500))
            async with httpx.AsyncClient(cookies=CONFIG.cookies) as client:
                result = await fetch_fund_metadata(client, ISIN, CONFIG)
        assert result == {}

    async def test_malformed_s_field_returns_empty_dict(self):
        payload = {"Data": {"S": "not-a-dict"}}
        with respx.mock:
            respx.get(METADATA_URL).mock(return_value=httpx.Response(200, json=payload))
            async with httpx.AsyncClient(cookies=CONFIG.cookies) as client:
                result = await fetch_fund_metadata(client, ISIN, CONFIG)
        assert result == {}

    async def test_empty_data_returns_all_empty_strings(self):
        with respx.mock:
            respx.get(METADATA_URL).mock(return_value=httpx.Response(200, json={}))
            async with httpx.AsyncClient(cookies=CONFIG.cookies) as client:
                result = await fetch_fund_metadata(client, ISIN, CONFIG)
        assert all(v == "" for v in result.values())
        assert len(result) == 8
