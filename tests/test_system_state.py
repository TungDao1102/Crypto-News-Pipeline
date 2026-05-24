"""Tests for SystemState singleton — REQ-3.01–3.05."""

import asyncio

import pytest

from src.system_state import SystemState


@pytest.fixture(autouse=True)
def reset_system_state():
    """Reset the singleton before each test for isolation.

    SystemState uses a class-level _instance singleton. Without resetting,
    state leaks between tests (e.g. increment_processed from one test
    affects the count seen by the next).
    """
    SystemState._instance = None
    yield


class TestSystemStateSingleton:
    """SystemState must be a singleton — same instance across calls."""

    def test_singleton_returns_same_instance(self):
        s1 = SystemState()
        s2 = SystemState()
        assert s1 is s2

    def test_singleton_across_reset(self):
        s1 = SystemState()
        # Force re-creation path by clearing _instance (shouldn't happen in practice)
        # but verifying the __new__ guard works
        assert SystemState._instance is s1


class TestSystemStateModeDefaults:
    """REQ-3.01: mode defaults to MANUAL on fresh instance."""

    @pytest.mark.asyncio
    async def test_default_mode_is_manual(self):
        state = SystemState()
        mode = await state.get_mode()
        assert mode == "MANUAL"

    @pytest.mark.asyncio
    async def test_initialized_flag_prevents_reinit(self):
        """__init__ should not reset mode after first construction."""
        state = SystemState()
        await state.set_mode("AUTO")
        # Create another reference — __init__ should be skipped
        state2 = SystemState()
        mode = await state2.get_mode()
        assert mode == "AUTO", "Singleton should not re-initialize mode"


class TestSystemStateSetGetMode:
    """REQ-3.02: set_mode/get_mode round-trip thread-safe."""

    @pytest.mark.asyncio
    async def test_set_mode_to_auto(self):
        state = SystemState()
        await state.set_mode("AUTO")
        assert await state.get_mode() == "AUTO"

    @pytest.mark.asyncio
    async def test_set_mode_to_manual(self):
        state = SystemState()
        await state.set_mode("AUTO")
        await state.set_mode("MANUAL")
        assert await state.get_mode() == "MANUAL"

    @pytest.mark.asyncio
    async def test_set_mode_round_trip_multiple(self):
        state = SystemState()
        for expected in ("MANUAL", "AUTO", "MANUAL", "AUTO"):
            await state.set_mode(expected)
            assert await state.get_mode() == expected


class TestSystemStateProcessedCount:
    """REQ-3.03–3.04: increment_processed / get_processed_count."""

    @pytest.mark.asyncio
    async def test_initial_count_is_zero(self):
        state = SystemState()
        count = await state.get_processed_count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_increment_increases_count(self):
        state = SystemState()
        await state.increment_processed()
        assert await state.get_processed_count() == 1

    @pytest.mark.asyncio
    async def test_multiple_increments(self):
        state = SystemState()
        for _ in range(5):
            await state.increment_processed()
        assert await state.get_processed_count() == 5

    @pytest.mark.asyncio
    async def test_increment_and_get_count_are_independent_of_mode(self):
        state = SystemState()
        await state.set_mode("AUTO")
        await state.increment_processed()
        await state.increment_processed()
        assert await state.get_mode() == "AUTO"
        assert await state.get_processed_count() == 2


class TestSystemStateThreadSafety:
    """REQ-3.05: asyncio.Lock ensures concurrent safety."""

    @pytest.mark.asyncio
    async def test_concurrent_increments_are_atomic(self):
        state = SystemState()
        async def increment_many(n):
            for _ in range(n):
                await state.increment_processed()

        await asyncio.gather(
            increment_many(10),
            increment_many(10),
            increment_many(10),
        )
        assert await state.get_processed_count() == 30

    @pytest.mark.asyncio
    async def test_concurrent_set_mode_safe(self):
        state = SystemState()
        async def toggle():
            for _ in range(10):
                await state.set_mode("AUTO")
                await state.set_mode("MANUAL")

        await asyncio.gather(toggle(), toggle(), toggle())
        # After all toggles, mode must be one of the valid values
        mode = await state.get_mode()
        assert mode in ("AUTO", "MANUAL")

    @pytest.mark.asyncio
    async def test_mixed_concurrent_read_write(self):
        state = SystemState()
        async def writer():
            for _ in range(10):
                await state.set_mode("AUTO")
                await state.increment_processed()
                await state.set_mode("MANUAL")
                await state.increment_processed()

        async def reader():
            for _ in range(10):
                await state.get_mode()
                await state.get_processed_count()

        await asyncio.gather(writer(), writer(), reader(), reader())
        count = await state.get_processed_count()
        assert count == 40, f"Expected 40, got {count}"
