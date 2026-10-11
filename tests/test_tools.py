"""The tools, and the bounds they hold."""

from __future__ import annotations

import pytest

from eme_mcp import eme, grid, server


class TestGrid:
    def test_reads_a_locator_to_the_centre_of_its_square(self) -> None:
        """EME-010: a locator names a rectangle; its centre is the honest point."""
        # DN13 spans 43-44 N and 118-116 W, so its centre is 43.5, -117.
        place = grid.place("DN13")
        assert (round(place.latitude, 4), round(place.longitude, 4)) == (43.5, -117.0)

    def test_a_subsquare_is_finer(self) -> None:
        """EME-011: six characters put you inside the four-character square."""
        coarse, fine = grid.place("DN13"), grid.place("DN13la")
        assert abs(fine.latitude - coarse.latitude) < 1.0
        assert abs(fine.longitude - coarse.longitude) < 2.0

    def test_case_does_not_matter(self) -> None:
        """EME-012: operators write locators both ways."""
        assert grid.place("dn13LA") == grid.place("DN13la")

    def test_what_is_not_a_locator_is_refused(self) -> None:
        """EME-013: refused, not guessed — a mis-read locator points at nothing."""
        for bad in ("", "  ", "DN", "1313", "ZZ99", "DN1", "DN13l", "../etc", "DN13la99x"):
            assert not grid.valid_locator(bad), bad
            with pytest.raises(grid.GridError):
                grid.place(bad)


class TestPathLoss:
    def test_echo_loss_matches_the_figures_operators_know(self) -> None:
        """EME-020: 2m, 70cm and 23cm land where EME literature puts them.

        These are not arbitrary: ~252, ~262 and ~271 dB at mean distance are
        the numbers in every EME link budget. If the radar equation here were
        wrong, it would show up as a station that cannot possibly hear itself.
        """
        expected = {"2m": 252.1, "70cm": 261.7, "23cm": 271.2}
        for band, frequency in eme.BANDS_MHZ.items():
            loss = eme.path_loss(eme.MEAN_DISTANCE_KM, frequency)
            assert abs(loss.echo_db - expected[band]) < 0.5, f"{band}: {loss.echo_db:.2f} dB"

    def test_round_trip_and_echo_are_different_things(self) -> None:
        """EME-021: twice the free-space loss is not the echo loss.

        They are confused often enough that both are returned, so the
        difference is asserted rather than assumed.
        """
        loss = eme.path_loss(eme.MEAN_DISTANCE_KM, 432.1)
        assert loss.round_trip_db == pytest.approx(2 * loss.one_way_db)
        assert loss.round_trip_db > loss.echo_db + 100.0

    def test_loss_rises_with_distance_and_frequency(self) -> None:
        """EME-022: the direction of both, which a sign error would invert."""
        near = eme.path_loss(eme.PERIGEE_KM, 432.1)
        far = eme.path_loss(eme.APOGEE_KM, 432.1)
        assert far.echo_db > near.echo_db
        assert eme.path_loss(eme.MEAN_DISTANCE_KM, 1296.1).echo_db > \
            eme.path_loss(eme.MEAN_DISTANCE_KM, 144.1).echo_db

    def test_a_nonsense_distance_is_refused(self) -> None:
        for bad in (0.0, -1.0):
            with pytest.raises(ValueError):
                eme.free_space_path_loss_db(bad, 432.1)


class TestDegradation:
    def test_perigee_is_the_best_case(self) -> None:
        """EME-030: 0 dB at perigee, and about 2 dB worse at apogee."""
        assert eme.degradation(eme.PERIGEE_KM, 0.0).distance_db == pytest.approx(0.0, abs=0.01)
        apogee = eme.degradation(eme.APOGEE_KM, 0.0).distance_db
        assert 2.0 < apogee < 2.6, f"apogee degradation {apogee:.2f} dB"

    def test_it_says_it_is_incomplete(self) -> None:
        """EME-031: sky noise is missing, and the answer must admit it.

        A degradation figure that looks complete and is not would be used to
        plan a schedule. The flag and the note are the product of that, so they
        are asserted rather than left to good intentions.
        """
        result = eme.degradation(eme.MEAN_DISTANCE_KM, 0.0)
        assert result.complete is False
        assert "sky noise" in result.note.lower()


class TestTools:
    def test_moon_window_returns_rows_and_bounds_them(self) -> None:
        """EME-040: the window is sampled, and a huge request is clamped."""
        answer = server.moon_window("DN13", hours=6, step_minutes=60)
        assert len(answer["rows"]) == 7
        assert {"time_utc", "azimuth_deg", "elevation_deg", "distance_km"} <= set(answer["rows"][0])
        huge = server.moon_window("DN13", hours=99_999, step_minutes=60 * 24)
        assert huge["hours"] <= 24 * 14

    def test_mutual_window_needs_both_ends(self) -> None:
        """EME-041: with a second locator, the rows say when both can see it."""
        answer = server.moon_window("DN13", hours=24, step_minutes=60, other_locator="IO91")
        assert answer["other_locator"] == "IO91"
        assert "mutual_rows" in answer
        for row in answer["rows"]:
            assert row["mutual"] == (row["elevation_deg"] > 0 and row["other_elevation_deg"] > 0)

    def test_an_antipodal_pair_shares_little_or_no_moon(self) -> None:
        """EME-042: not vacuous — the mutual window really does exclude.

        Two stations on opposite sides of the Earth cannot both see the moon
        for most of a day. If every pair came back fully mutual, the
        intersection would be doing nothing.
        """
        answer = server.moon_window("DN13", hours=24, step_minutes=60, other_locator="RE78")
        assert answer["mutual_rows"] < answer["above_horizon_rows"]

    def test_path_loss_tool_takes_a_band_or_a_frequency(self) -> None:
        """EME-043: both routes, and nonsense refused."""
        assert server.path_loss(band="2m")["frequency_mhz"] == eme.BANDS_MHZ["2m"]
        assert server.path_loss(frequency_mhz=1296.0)["frequency_mhz"] == 1296.0
        assert "error" in server.path_loss(band="11m")
        assert "error" in server.path_loss(frequency_mhz=1.0)
        assert "error" in server.path_loss(frequency_mhz=99_999.0)

    def test_topocentric_when_a_locator_is_given(self) -> None:
        """EME-044: a locator changes the range, because it should."""
        without = server.path_loss(band="70cm")
        with_grid = server.path_loss(band="70cm", locator="DN13")
        assert with_grid["seen_from"] == "DN13"
        assert without["seen_from"] is None
        assert with_grid["distance_km"] != without["distance_km"]

    def test_a_bad_time_is_refused_rather_than_guessed(self) -> None:
        """EME-045: a misread time gives a confidently wrong answer."""
        for bad in ("yesterday", "2026-13-45", "not-a-time"):
            assert "error" in server.path_loss(band="2m", when=bad)
            assert "error" in server.degradation(when=bad)

    def test_calendar_is_bounded_and_ranked(self) -> None:
        """EME-046: a year at most, best days first, and honest about sky noise."""
        answer = server.calendar(days=10)
        assert len(answer["calendar"]) == 10
        best = [row["degradation_db"] for row in answer["best_days"]]
        assert best == sorted(best)
        assert answer["complete"] is False
        assert server.calendar(days=99_999)["days"] <= 365

    def test_nulls_are_treated_as_defaults(self) -> None:
        """EME-047: llama.cpp and mcpo send null for optional parameters."""
        assert "error" not in server.moon_window("DN13", hours=None, step_minutes=None)
        assert "error" not in server.calendar(days=None)
        assert "error" not in server.degradation(locator=None, when=None)

    def test_version_info(self) -> None:
        """EME-048: fleet identity attestation."""
        info = server.get_version_info()
        assert info["service_name"] == "eme-mcp"
        assert "Meeus" in info["spec_version"]
