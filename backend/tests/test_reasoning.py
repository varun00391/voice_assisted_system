from app.providers.llm.reasoning import strip_reasoning


def test_plain_answer_is_unchanged():
    assert strip_reasoning("Just the answer.") == ("Just the answer.", False)


def test_think_block_is_removed():
    assert strip_reasoning("<think>\nhmm\n</think>\nAnswer") == ("\nAnswer", False)


def test_closing_tag_only():
    assert strip_reasoning("reasoning without opening tag</think>Answer") == ("Answer", False)


def test_unclosed_block_means_output_stopped_while_reasoning():
    assert strip_reasoning("Intro <think>still thinking") == ("Intro ", True)
