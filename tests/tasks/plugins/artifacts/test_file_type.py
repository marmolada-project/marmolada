from unittest import mock
from uuid import uuid1

import pytest
from PIL import Image

from marmolada.tasks.plugins.artifacts import file_type


@pytest.mark.parametrize(
    "content_type",
    ("text/plain", "image/jpeg", "image/tiff", "image/x-adobe-dng", "image/x-sony-arw"),
)
@pytest.mark.parametrize("uppercase", (False, True), ids=("lowercase", "uppercase"))
async def test_process(content_type, uppercase, tmp_path, caplog):
    if content_type == "text/plain":
        tmp_file_name = "TMP_FILE" if uppercase else "tmp_file"
        tmp_file = tmp_path / tmp_file_name
        tmp_file.write_text("Hello")
    elif content_type.startswith("image/"):
        exp_fmt = content_type.split("/")[1]
        write_fmt = exp_fmt
        match exp_fmt:
            case "jpeg":
                ext = ".jpg"
            case "tiff":
                ext = ".tif"
            case "x-adobe-dng":
                ext = ".dng"
                write_fmt = "tiff"
            case "x-sony-arw":
                ext = ".arw"
                write_fmt = "tiff"
            case _:
                raise ValueError(f"{exp_fmt=}")

        tmp_file_name = f"tmp_file{ext}"
        if uppercase:
            tmp_file_name = tmp_file_name.upper()
        tmp_file = tmp_path / tmp_file_name

        image = Image.new(mode="RGB", size=(8, 8), color="white")
        image.save(tmp_file, format=write_fmt)

    db_session = mock.AsyncMock()
    db_session.__str__.return_value = "DB_SESSION"

    db_session.execute.return_value = result = mock.Mock()
    result.scalar_one.return_value = artifact = mock.Mock()
    artifact.full_path = tmp_file

    uuid = uuid1()

    with caplog.at_level("DEBUG"):
        await file_type.process(db_session=db_session, uuid=uuid)

    assert artifact.content_type == content_type
    assert f"process(db_session=DB_SESSION, uuid={uuid})" in caplog.messages
    assert f"-> {content_type}" in caplog.messages
