from scripts.seedance2_smoke import MODEL_VERSIONS, derive_cdn_url


def test_seedance2_smoke_model_versions_skip_failed_1_0_lite():
    assert MODEL_VERSIONS == {
        "seedance-1.5-pro": "seedance-1-5-pro",
        "seedance-2.0": "seedance-2-0",
        "seedance-2.0-fast": "seedance-2-0-fast",
    }
    assert "seedance-1-0-lite" not in MODEL_VERSIONS.values()


def test_seedance2_smoke_derives_cdn_url_from_r2_presigned_url():
    url = (
        "https://seedance2.abc.r2.cloudflarestorage.com/images/2026-06-12/file.jpg"
        "?X-Amz-Signature=secret"
    )
    assert derive_cdn_url(url) == "https://cdn.seedance2.ai/images/2026-06-12/file.jpg"
