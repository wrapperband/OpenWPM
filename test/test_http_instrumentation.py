import pytest # NOQA
import os
import utilities
import expected
from openwpmtest import OpenWPMTest
from ..automation import TaskManager
from ..automation.platform_utils import parse_http_stack_trace_str


class TestHTTPInstrument(OpenWPMTest):
    NUM_BROWSERS = 1

    def get_config(self, data_dir):
        manager_params, browser_params = TaskManager.load_default_params(self.NUM_BROWSERS)
        manager_params['data_directory'] = data_dir
        manager_params['log_directory'] = data_dir
        browser_params[0]['headless'] = True
        browser_params[0]['extension']['enabled'] = True
        browser_params[0]['extension']['httpInstrument'] = True
        manager_params['db'] = os.path.join(manager_params['data_directory'],
                                            manager_params['database_name'])
        return manager_params, browser_params

    def test_page_visit(self, tmpdir):
        test_url = utilities.BASE_TEST_URL + '/http_test_page.html'
        db = self.visit(test_url, str(tmpdir))

        # HTTP Requests
        rows = utilities.query_db(db, (
            "SELECT url, top_level_url, is_XHR, is_frame_load, is_full_page, "
            "is_third_party_channel, is_third_party_window, triggering_origin "
            "loading_origin, loading_href, content_policy_type FROM http_requests_ext"))
        observed_records = set()
        for row in rows:
            observed_records.add(row)
        assert expected.http_requests == observed_records

        # HTTP Responses
        rows = utilities.query_db(db,
            "SELECT url, referrer, location FROM http_responses_ext")
        observed_records = set()
        for row in rows:
            observed_records.add(row)
        assert expected.http_responses == observed_records

    #TODO: test that cache hits are recorded. Will need a custom command to
    #refresh page.

    #TODO: test that javascript content is saved correctly

    def test_http_stacktrace(self, tmpdir):
        test_url = utilities.BASE_TEST_URL + '/http_stacktrace.html'
        db = self.visit(test_url, str(tmpdir), sleep_after=3)
        rows = utilities.query_db(db, (
            "SELECT url, req_call_stack FROM http_requests_ext"))
        for row in rows:
            url, stacktrace = row
            if url.endswith("inject_pixel.js"):
                assert stacktrace == expected.stack_trace_inject_js
            if url.endswith("test_image.png"):
                assert stacktrace == expected.stack_trace_inject_image
            if url.endswith("Blank.gif"):
                assert stacktrace == expected.stack_trace_inject_pixel

    def test_parse_http_stack_trace_str(self, tmpdir):
        stacktrace = expected.stack_trace_inject_image
        stack_frames = parse_http_stack_trace_str(stacktrace)
        assert stack_frames == expected.call_stack_inject_image

    def test_http_stacktrace_nonjs_loads(self, tmpdir):
        # stacktrace should be empty for requests NOT triggered by scripts
        test_url = utilities.BASE_TEST_URL + '/http_test_page.html'
        db = self.visit(test_url, str(tmpdir), sleep_after=3)
        rows = utilities.query_db(db, (
            "SELECT url, req_call_stack FROM http_requests_ext"))
        for row in rows:
            _, stacktrace = row
            assert stacktrace == ""