from app.server import LOSSY_CODECS


def test_lossy_codecs_is_frozenset():
    assert isinstance(LOSSY_CODECS, frozenset)


def test_lossy_codecs_contents():
    assert LOSSY_CODECS == frozenset({"mp3", "aac", "opus", "vorbis", "m4a"})


def test_mp3_is_lossy():
    assert "mp3" in LOSSY_CODECS


def test_flac_is_not_lossy():
    assert "flac" not in LOSSY_CODECS


def test_wav_is_not_lossy():
    assert "wav" not in LOSSY_CODECS
