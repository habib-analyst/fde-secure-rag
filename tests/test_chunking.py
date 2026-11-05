from fde_secure_rag.chunking import chunk_document, chunk_text


def test_chunking_is_deterministic():
    text = " ".join(f"word{i}" for i in range(200))
    assert chunk_text(text) == chunk_text(text)
    assert chunk_document("doc-x", text) == chunk_document("doc-x", text)


def test_chunk_ids_are_stable_and_formatted():
    pairs = chunk_document("doc-x", "one two three four five")
    assert pairs == [("doc-x#chunk_0", "one two three four five")]


def test_chunk_windows_and_overlap_are_pinned():
    # 120 words, 50-word windows, 10-word overlap (40-word step):
    # windows start at 0, 40, 80 -> exactly 3 chunks.
    text = " ".join(f"w{i}" for i in range(120))
    chunks = chunk_text(text)
    assert len(chunks) == 3
    assert chunks[0].split()[0] == "w0" and chunks[0].split()[-1] == "w49"
    assert chunks[1].split()[0] == "w40" and chunks[1].split()[-1] == "w89"
    assert chunks[2].split()[0] == "w80" and chunks[2].split()[-1] == "w119"
    assert len(chunks[0].split()) == 50
    assert len(chunks[2].split()) == 40


def test_chunking_empty_text_yields_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []
    assert chunk_document("doc-x", "") == []
