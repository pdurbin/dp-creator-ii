import csv
import polars as pl
import polars.testing as pl_testing
import tempfile
import pytest

from dp_creator_ii.utils.csv_helper import read_field_names


# We will not reference the encoding when reading:
# We need to be robust against any input.
@pytest.mark.parametrize("write_encoding", ["latin1", "utf8", "utf-8-sig"])
def test_csv_loading(write_encoding):
    with tempfile.NamedTemporaryFile(
        mode="w", newline="", encoding=write_encoding
    ) as fp:
        data = {"NAME": ["André"], "AGE": [42]}
        write_lf = pl.DataFrame(data).lazy()

        writer = csv.writer(fp)
        writer.writerow(data.keys())
        for row in write_lf.collect().rows():
            writer.writerow(row)
        fp.flush()

        # NOT WHAT WE'RE DOING!
        # w/o "ignore_errors=True" it fails outright for latin1.
        read_lf = pl.scan_csv(fp.name)
        if write_encoding == "latin1":
            with pytest.raises(pl.exceptions.ComputeError):
                pl_testing.assert_frame_equal(write_lf, read_lf)

        # ALSO NOT WHAT WE'RE DOING!
        # w/ "ignore_errors=True" but w/o "utf8-lossy" it reads,
        # but whole cell is empty if mis-encoded.
        read_lf = pl.scan_csv(fp.name, ignore_errors=True)
        if write_encoding == "latin1":
            pl_testing.assert_frame_not_equal(write_lf, read_lf)
            assert read_lf.collect().rows()[0] == (None, 42)

        # THIS IS THE RIGHT PATTERN!
        # Not perfect, but "utf8-lossy" retains as much info as possible.
        read_lf = pl.scan_csv(fp.name, encoding="utf8-lossy")
        if write_encoding == "latin1":
            # Not equal, but the only differce is the "�".
            pl_testing.assert_frame_not_equal(write_lf, read_lf)
            assert read_lf.collect().rows()[0] == ("Andr�", 42)
        else:
            pl_testing.assert_frame_equal(write_lf, read_lf)

        # Preceding lines are reading the whole DF via Polars.
        field_names_read = read_field_names(fp.name)
        assert field_names_read == list(data.keys())
