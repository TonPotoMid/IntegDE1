import pytest

from pipeline.faults import FaultInjector
from pipeline.retry import retry


def test_retry_succeeds_after_failures():
    calls, sleeps = [], []

    @retry(attempts=3, delay=1, backoff=2, exceptions=(ValueError,), sleep=sleeps.append)
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("boom")
        return "ok"

    assert flaky() == "ok"
    assert len(calls) == 3
    assert sleeps == [1, 2]  # backoff exponentiel


def test_retry_gives_up():
    @retry(attempts=2, delay=0, exceptions=(ValueError,), sleep=lambda _: None)
    def always_fail():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        always_fail()


def test_retry_does_not_catch_other_exceptions():
    calls = []

    @retry(attempts=5, delay=0, exceptions=(ValueError,), sleep=lambda _: None)
    def type_error():
        calls.append(1)
        raise TypeError()

    with pytest.raises(TypeError):
        type_error()
    assert len(calls) == 1


def test_fault_injector():
    inj = FaultInjector("UNUSED_VAR")
    inj.reset(2)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            inj.maybe_fail(RuntimeError)
    inj.maybe_fail(RuntimeError)  # ne lève plus
