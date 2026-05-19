from app.server import build_probe_response


def test_lossy_opus_source():
    info = {
        "title": "Hold On Tight",
        "artist": "Hidde van Wee",
        "duration": 287.4,
        "acodec": "opus",
        "abr": 128.0,
        "thumbnail": "https://example.com/cover.jpg",
        "ext": "opus",
    }
    result = build_probe_response(info)
    assert result["title"] == "Hold On Tight"
    assert result["artist"] == "Hidde van Wee"
    assert result["duration"] == 287.4
    assert result["codec"] == "opus"
    assert result["bitrate"] == 128000
    assert result["thumbnail"] == "https://example.com/cover.jpg"
    assert result["ext"] == "opus"
    assert result["lossy"] is True


def test_lossless_flac_source():
    info = {
        "title": "Symphony No. 9",
        "uploader": "Berlin Philharmonic",
        "duration": 4200.0,
        "acodec": "flac",
        "abr": 1411.0,
        "thumbnail": "https://example.com/symphony.jpg",
        "ext": "flac",
    }
    result = build_probe_response(info)
    assert result["codec"] == "flac"
    assert result["bitrate"] == 1411000
    assert result["lossy"] is False
    assert result["artist"] == "Berlin Philharmonic"


def test_uploader_falls_back_to_artist():
    info = {"title": "X", "uploader": "Some Channel", "acodec": "mp3", "abr": 320}
    result = build_probe_response(info)
    assert result["artist"] == "Some Channel"


def test_creator_preferred_over_uploader():
    info = {"title": "X", "creator": "True Artist", "uploader": "Channel", "acodec": "mp3", "abr": 320}
    result = build_probe_response(info)
    assert result["artist"] == "True Artist"


def test_artist_field_preferred_when_present():
    info = {"title": "X", "artist": "Tagged Artist", "uploader": "Channel", "acodec": "mp3"}
    result = build_probe_response(info)
    assert result["artist"] == "Tagged Artist"


def test_missing_codec_defaults_to_lossy():
    info = {"title": "X", "uploader": "Y"}
    result = build_probe_response(info)
    assert result["codec"] is None
    assert result["lossy"] is True


def test_unknown_codec_defaults_to_lossy():
    info = {"title": "X", "uploader": "Y", "acodec": "unknownformat"}
    result = build_probe_response(info)
    assert result["codec"] == "unknownformat"
    assert result["lossy"] is True


def test_bitrate_missing_returns_none():
    info = {"title": "X", "uploader": "Y", "acodec": "flac"}
    result = build_probe_response(info)
    assert result["bitrate"] is None


def test_uppercase_codec_normalised():
    info = {"title": "X", "uploader": "Y", "acodec": "MP3", "abr": 320}
    result = build_probe_response(info)
    assert result["codec"] == "mp3"
    assert result["lossy"] is True


def test_thumbnail_falls_back_to_thumbnails_list():
    info = {
        "title": "X",
        "uploader": "Y",
        "acodec": "opus",
        "thumbnails": [
            {"url": "https://example.com/small.jpg", "width": 100},
            {"url": "https://example.com/large.jpg", "width": 1000},
        ],
    }
    result = build_probe_response(info)
    assert result["thumbnail"] == "https://example.com/large.jpg"


def test_acodec_none_sentinel_falls_back_to_codec():
    info = {"title": "X", "uploader": "Y", "acodec": "none", "codec": "opus"}
    result = build_probe_response(info)
    assert result["codec"] == "opus"
    assert result["lossy"] is True


def test_codec_none_sentinel_treated_as_missing():
    info = {"title": "X", "uploader": "Y", "acodec": "none", "codec": "none"}
    result = build_probe_response(info)
    assert result["codec"] is None
    assert result["lossy"] is True


def test_bitrate_zero_returns_zero():
    info = {"title": "X", "uploader": "Y", "acodec": "opus", "abr": 0}
    result = build_probe_response(info)
    assert result["bitrate"] == 0
