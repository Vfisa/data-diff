import logging
import re
from typing import Iterable, Sequence
from urllib.parse import urlparse
import operator
import threading
from datetime import datetime
import json


def safezip(*args):
    "zip but makes sure all sequences are the same length"
    lens = list(map(len, args))
    if len(set(lens)) != 1:
        raise ValueError(f"Mismatching lengths in arguments to safezip: {lens}")
    return zip(*args)


def _join_if_any(sym, args):
    args = list(args)
    if not args:
        return ""
    return sym.join(str(a) for a in args if a)


def remove_password_from_url(url: str, replace_with: str = "***") -> str:
    parsed = urlparse(url)
    account = parsed.username or ""
    if parsed.password:
        account += ":" + replace_with
    host = _join_if_any(":", filter(None, [parsed.hostname, parsed.port]))
    netloc = _join_if_any("@", filter(None, [account, host]))
    replaced = parsed._replace(netloc=netloc)
    return replaced.geturl()


def match_like(pattern: str, strs: Sequence[str]) -> Iterable[str]:
    reo = re.compile(pattern.replace("%", ".*").replace("?", ".") + "$")
    for s in strs:
        if reo.match(s):
            yield s


def accumulate(iterable, func=operator.add, *, initial=None):
    "Return running totals"
    # Taken from https://docs.python.org/3/library/itertools.html#itertools.accumulate, to backport 'initial' to 3.7
    it = iter(iterable)
    total = initial
    if initial is None:
        try:
            total = next(it)
        except StopIteration:
            return
    yield total
    for element in it:
        total = func(total, element)
        yield total


def run_as_daemon(threadfunc, *args):
    th = threading.Thread(target=threadfunc, args=args)
    th.daemon = True
    th.start()
    return th


def getLogger(name):
    return logging.getLogger(name.rsplit(".", 1)[-1])


def eval_name_template(name):
    def get_timestamp(_match):
        return datetime.now().isoformat("_", "seconds").replace(":", "_")

    return re.sub("%t", get_timestamp, name)


def _jsons_equal(a, b):
    try:
        return json.loads(a) == json.loads(b)
    except (ValueError, TypeError, json.decoder.JSONDecodeError):  # not valid jsons
        return False


def diffs_are_equiv_jsons(v):
    if (len(v) != 2) or ({v[0][0], v[1][0]} != {'+', '-'}):  # ignore rows that are missing in one of the tables
        return False
    # check all extra columns.  TODO: would be more efficient if we pass the indices of json cols to only compare those
    match = True
    for col_a, col_b in safezip(v[0][1][1:], v[1][1][1:]):
        match = (col_a == col_b) or _jsons_equal(col_a, col_b)
        if not match:
            break
    return match
