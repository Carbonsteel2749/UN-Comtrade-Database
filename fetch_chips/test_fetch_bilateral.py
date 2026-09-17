"""离线测试：不读取真实密钥，不调用UN Comtrade服务。"""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

import pandas as pd

try:
    from . import fetch_api as api, fetch_url as url
except ImportError:
    import fetch_api as api
    import fetch_url as url


def rows(params, partners=(0, 156, 842)):
    return pd.DataFrame([
        dict(period=int(params["period"]), reporterCode=int(reporter), partnerCode=partner,
             cmdCode=code, flowCode=params["flowCode"], partner2Code=0, customsCode="C00",
             motCode=0, primaryValue=123.45, isAggregate=True)
        for reporter in params["reporterCode"].split(",")
        for code in params["cmdCode"].split(",") for partner in partners
    ])


class BilateralTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.patch = patch.multiple(api, OUTPUT_DIR=Path(self.temp.name), SUBSCRIPTION_KEY="test-key",
                                    reporters={"36": "Australia"}, REQUEST_INTERVAL=0)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        api._stop.clear()
        api._next_request = 0
        self.params = api.make_params("2020", ["36"], ["381800"], "X")

    def test_all_partners_parameters_and_world_filter(self):
        self.assertIsNone(self.params["partnerCode"])
        frame = api.fetch_batch(self.params, rows, "api")
        self.assertEqual(set(frame.partnerCode), {156, 842})
        # 商品的isAggregate标志不能用于排除国家伙伴，否则HS6记录会被误删。
        self.assertTrue(frame.isAggregate.all())

    def test_both_backends_use_22_products_and_both_flows(self):
        for backend in ("api", "url"):
            calls = []
            def request(params):
                calls.append(params)
                return rows(params)
            frames = api.fetch_by_year("2020", request, backend)
            data = pd.concat(frames, ignore_index=True)
            self.assertEqual(set(data.cmdCode), set(api.CHIP_CODES))
            self.assertEqual(set(data.flowCode), {"X", "M"})
            self.assertNotIn(0, set(data.partnerCode))
            self.assertTrue(all(p["partnerCode"] is None for p in calls))
            self.assertFalse(any("TOTAL" in p["cmdCode"] for p in calls))

    def test_cache_resume_and_separation_from_old_totals(self):
        old = api.OUTPUT_DIR / "api_batches"
        old.mkdir()
        (old / "old.json").write_text('{"not": "bilateral"}')
        request = Mock(side_effect=rows)
        first = api.fetch_batch(self.params, request, "api")
        second = api.fetch_batch(self.params, request, "api")
        self.assertEqual(request.call_count, 1)
        pd.testing.assert_frame_equal(first.reset_index(drop=True), second.reset_index(drop=True))
        self.assertTrue(list((api.OUTPUT_DIR / "api_bilateral_batches").glob("*.json")))

    def test_truncation_checked_before_filter_and_split_reporters(self):
        params = dict(self.params, reporterCode="36,124", maxRecords=4)
        calls = []
        def request(query):
            calls.append(query)
            return rows(query).iloc[:query["maxRecords"]]
        data = api.fetch_batch(params, request, "api")
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(data), 4)
        self.assertEqual(set(data.reporterCode), {36, 124})
        self.assertNotIn(0, set(data.partnerCode))

    def test_truncation_split_products(self):
        params = dict(self.params, cmdCode="381800,370710", maxRecords=4)
        request = Mock(side_effect=lambda q: rows(q).iloc[:q["maxRecords"]])
        data = api.fetch_batch(params, request, "url")
        self.assertEqual(request.call_count, 3)
        self.assertEqual(set(data.cmdCode), {"381800", "370710"})

    def test_unsplittable_truncation_not_cached(self):
        params = dict(self.params, maxRecords=2)
        with self.assertRaises(RuntimeError):
            api.fetch_batch(params, lambda q: rows(q).iloc[:2], "api")
        self.assertFalse(list(api.OUTPUT_DIR.rglob("*.json")))

    def test_none_is_failure_but_empty_is_cached(self):
        with self.assertRaises(RuntimeError):
            api.fetch_batch(self.params, lambda q: None, "api")
        self.assertFalse(list(api.OUTPUT_DIR.rglob("*.json")))
        request = Mock(return_value=pd.DataFrame())
        self.assertTrue(api.fetch_batch(self.params, request, "api").empty)
        self.assertTrue(api.fetch_batch(self.params, request, "api").empty)
        self.assertEqual(request.call_count, 1)

    def test_reject_wrong_dimension(self):
        frame = rows(self.params)
        frame["cmdCode"] = "TOTAL"
        with self.assertRaises(RuntimeError):
            api.fetch_batch(self.params, lambda q: frame, "api")
        self.assertFalse(list(api.OUTPUT_DIR.rglob("*.json")))

    def test_url_request_matches_api_and_keeps_key_out_of_url(self):
        response = Mock(status_code=200)
        response.json.return_value = {"data": rows(self.params).to_dict("records")}
        with patch.object(url.requests, "get", return_value=response) as get:
            data = api.fetch_batch(self.params, url.request_url, "url")
        query = parse_qs(urlsplit(get.call_args.args[0]).query)
        self.assertNotIn("partnerCode", query)
        self.assertNotIn("subscription-key", query)
        self.assertEqual(query["cmdCode"], ["381800"])
        self.assertEqual(query["partner2Code"], ["0"])
        self.assertEqual(query["customsCode"], ["C00"])
        self.assertEqual(get.call_args.kwargs["headers"]["Ocp-Apim-Subscription-Key"], "test-key")
        self.assertNotIn(0, set(data.partnerCode))

    def test_url_429_retry_and_quota_stop(self):
        limited = Mock(status_code=429, headers={"Retry-After": "0"}, text="Too many requests")
        ok = Mock(status_code=200)
        ok.json.return_value = {"data": []}
        with patch.object(url.requests, "get", side_effect=[limited, ok]) as get:
            self.assertTrue(url.request_url(self.params).empty)
            self.assertEqual(get.call_count, 2)
        quota = Mock(status_code=429, headers={"Retry-After": "3600"}, text="Quota exceeded")
        with patch.object(url.requests, "get", return_value=quota) as get:
            with self.assertRaises(RuntimeError):
                url.request_url(self.params)
            self.assertEqual(get.call_count, 1)
            self.assertTrue(api._stop.is_set())

    def test_main_writes_only_bilateral_rows_for_each_backend(self):
        reporters = Path(self.temp.name) / "reporters.csv"
        reporters.write_text("id,text\n36,Australia\n", encoding="utf-8")
        with patch.multiple(api, REPORTERS_CSV=reporters, periods=["2020"], start_year=2020, end_year=2020), \
             patch.object(api, "load_dotenv"), patch.dict(os.environ, {"API_KEY": "test-key"}):
            for backend in ("api", "url"):
                self.assertEqual(api.main(request=rows, backend=backend), 0)
                saved = pd.read_csv(api.OUTPUT_DIR / f"chips_bilateral_{backend}_2020_2020.csv")
                self.assertEqual(set(saved.partnerCode), {156, 842})
                self.assertEqual(set(saved.flowCode), {"X", "M"})
                self.assertEqual(len(saved), 22 * 2 * 2)


if __name__ == "__main__":
    unittest.main()
