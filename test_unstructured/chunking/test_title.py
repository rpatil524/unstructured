# pyright: reportPrivateUsage=false

"""Test suite for the `unstructured.chunking.title` module."""

from __future__ import annotations

from typing import Any, Optional

import pytest

from test_unstructured.unit_utils import FixtureRequest, Mock, function_mock, input_path
from unstructured.chunking.base import CHUNK_MULTI_PAGE_DEFAULT
from unstructured.chunking.title import _ByTitleChunkingOptions, chunk_by_title
from unstructured.documents.coordinates import CoordinateSystem
from unstructured.documents.elements import (
    CheckBox,
    CompositeElement,
    CoordinatesMetadata,
    Element,
    ElementMetadata,
    ListItem,
    Table,
    TableChunk,
    Text,
    Title,
)
from unstructured.partition.html import partition_html
from unstructured.staging.base import elements_from_json

# ================================================================================================
# INTEGRATION-TESTS
# ================================================================================================
# These test `chunk_by_title()` as an integrated whole, calling `chunk_by_title()` and inspecting
# the outputs.
# ================================================================================================


def test_it_chunks_text_followed_by_table_together_when_both_fit():
    elements = elements_from_json(input_path("chunking/title_table_200.json"))

    chunks = chunk_by_title(elements, combine_text_under_n_chars=0)

    assert len(chunks) == 1
    assert isinstance(chunks[0], CompositeElement)


def test_it_chunks_table_followed_by_text_together_when_both_fit():
    elements = elements_from_json(input_path("chunking/table_text_200.json"))

    # -- disable chunk combining so we test pre-chunking behavior, not chunk-combining --
    chunks = chunk_by_title(elements, combine_text_under_n_chars=0)

    assert len(chunks) == 1
    assert isinstance(chunks[0], CompositeElement)


def test_it_splits_oversized_table():
    elements = elements_from_json(input_path("chunking/table_2000.json"))

    chunks = chunk_by_title(elements)

    assert len(chunks) == 5
    assert all(isinstance(chunk, TableChunk) for chunk in chunks)


def test_it_starts_new_chunk_for_table_after_full_text_chunk():
    elements = elements_from_json(input_path("chunking/long_text_table_200.json"))

    chunks = chunk_by_title(elements, max_characters=250)

    assert len(chunks) == 2
    assert [type(chunk) for chunk in chunks] == [CompositeElement, Table]


def test_it_starts_new_chunk_for_text_after_full_table_chunk():
    elements = elements_from_json(input_path("chunking/full_table_long_text_250.json"))

    chunks = chunk_by_title(elements, max_characters=250)

    assert len(chunks) == 2
    assert [type(chunk) for chunk in chunks] == [Table, CompositeElement]


def test_it_splits_a_large_text_element_into_multiple_chunks():
    elements: list[Element] = [
        Title("Introduction"),
        Text(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit. In rhoncus ipsum sed lectus"
            " porta volutpat.",
        ),
    ]

    chunks = chunk_by_title(elements, max_characters=50)

    assert chunks == [
        CompositeElement("Introduction"),
        CompositeElement("Lorem ipsum dolor sit amet consectetur adipiscing"),
        CompositeElement("elit. In rhoncus ipsum sed lectus porta volutpat."),
    ]


def test_it_splits_elements_by_title_and_table():
    elements: list[Element] = [
        Title("A Great Day"),
        Text("Today is a great day."),
        Text("It is sunny outside."),
        Table("Heading\nCell text"),
        Title("An Okay Day"),
        Text("Today is an okay day."),
        Text("It is rainy outside."),
        Title("A Bad Day"),
        Text("Today is a bad day."),
        Text("It is storming outside."),
        CheckBox(),
    ]

    chunks = chunk_by_title(elements, combine_text_under_n_chars=0, include_orig_elements=True)

    assert len(chunks) == 3
    # --
    chunk = chunks[0]
    assert isinstance(chunk, CompositeElement)
    assert chunk.metadata.orig_elements == [
        Title("A Great Day"),
        Text("Today is a great day."),
        Text("It is sunny outside."),
        Table("Heading\nCell text"),
    ]
    # --
    chunk = chunks[1]
    assert isinstance(chunk, CompositeElement)
    assert chunk.metadata.orig_elements == [
        Title("An Okay Day"),
        Text("Today is an okay day."),
        Text("It is rainy outside."),
    ]
    # --
    chunk = chunks[2]
    assert isinstance(chunk, CompositeElement)
    assert chunk.metadata.orig_elements == [
        Title("A Bad Day"),
        Text("Today is a bad day."),
        Text("It is storming outside."),
        CheckBox(),
    ]


def test_chunk_by_title():
    elements: list[Element] = [
        Title("A Great Day", metadata=ElementMetadata(emphasized_text_contents=["Day"])),
        Text("Today is a great day.", metadata=ElementMetadata(emphasized_text_contents=["day"])),
        Text("It is sunny outside."),
        Table("Heading\nCell text"),
        Title("An Okay Day"),
        Text("Today is an okay day."),
        Text("It is rainy outside."),
        Title("A Bad Day"),
        Text("Today is a bad day."),
        Text("It is storming outside."),
        CheckBox(),
    ]

    chunks = chunk_by_title(elements, combine_text_under_n_chars=0, include_orig_elements=False)

    assert chunks == [
        CompositeElement(
            "A Great Day\n\nToday is a great day.\n\nIt is sunny outside.\n\nHeading Cell text"
        ),
        CompositeElement("An Okay Day\n\nToday is an okay day.\n\nIt is rainy outside."),
        CompositeElement(
            "A Bad Day\n\nToday is a bad day.\n\nIt is storming outside.",
        ),
    ]
    assert chunks[0].metadata == ElementMetadata(emphasized_text_contents=["Day", "day"])


def test_chunk_by_title_separates_by_page_number():
    elements: list[Element] = [
        Title("A Great Day", metadata=ElementMetadata(page_number=1)),
        Text("Today is a great day.", metadata=ElementMetadata(page_number=2)),
        Text("It is sunny outside.", metadata=ElementMetadata(page_number=2)),
        Table("Heading\nCell text"),
        Title("An Okay Day"),
        Text("Today is an okay day."),
        Text("It is rainy outside."),
        Title("A Bad Day"),
        Text("Today is a bad day."),
        Text("It is storming outside."),
        CheckBox(),
    ]
    chunks = chunk_by_title(elements, multipage_sections=False, combine_text_under_n_chars=0)

    assert chunks == [
        CompositeElement(
            "A Great Day",
        ),
        CompositeElement("Today is a great day.\n\nIt is sunny outside.\n\nHeading Cell text"),
        CompositeElement("An Okay Day\n\nToday is an okay day.\n\nIt is rainy outside."),
        CompositeElement(
            "A Bad Day\n\nToday is a bad day.\n\nIt is storming outside.",
        ),
    ]


def test_chuck_by_title_respects_multipage():
    elements: list[Element] = [
        Title("A Great Day", metadata=ElementMetadata(page_number=1)),
        Text("Today is a great day.", metadata=ElementMetadata(page_number=2)),
        Text("It is sunny outside.", metadata=ElementMetadata(page_number=2)),
        Table("Heading\nCell text"),
        Title("An Okay Day"),
        Text("Today is an okay day."),
        Text("It is rainy outside."),
        Title("A Bad Day"),
        Text("Today is a bad day."),
        Text("It is storming outside."),
        CheckBox(),
    ]
    chunks = chunk_by_title(elements, multipage_sections=True, combine_text_under_n_chars=0)
    assert chunks == [
        CompositeElement(
            "A Great Day\n\nToday is a great day.\n\nIt is sunny outside.\n\nHeading Cell text"
        ),
        CompositeElement("An Okay Day\n\nToday is an okay day.\n\nIt is rainy outside."),
        CompositeElement(
            "A Bad Day\n\nToday is a bad day.\n\nIt is storming outside.",
        ),
    ]


def test_chunk_by_title_groups_across_pages():
    elements: list[Element] = [
        Title("A Great Day", metadata=ElementMetadata(page_number=1)),
        Text("Today is a great day.", metadata=ElementMetadata(page_number=2)),
        Text("It is sunny outside.", metadata=ElementMetadata(page_number=2)),
        Table("Heading\nCell text"),
        Title("An Okay Day"),
        Text("Today is an okay day."),
        Text("It is rainy outside."),
        Title("A Bad Day"),
        Text("Today is a bad day."),
        Text("It is storming outside."),
        CheckBox(),
    ]
    chunks = chunk_by_title(elements, multipage_sections=True, combine_text_under_n_chars=0)

    assert chunks == [
        CompositeElement(
            "A Great Day\n\nToday is a great day.\n\nIt is sunny outside.\n\nHeading Cell text"
        ),
        CompositeElement("An Okay Day\n\nToday is an okay day.\n\nIt is rainy outside."),
        CompositeElement(
            "A Bad Day\n\nToday is a bad day.\n\nIt is storming outside.",
        ),
    ]


def test_add_chunking_strategy_on_partition_html():
    filename = "example-docs/example-10k-1p.html"
    chunk_elements = partition_html(filename, chunking_strategy="by_title")
    elements = partition_html(filename)
    chunks = chunk_by_title(elements)
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_add_chunking_strategy_respects_max_characters():
    filename = "example-docs/example-10k-1p.html"
    chunk_elements = partition_html(
        filename,
        chunking_strategy="by_title",
        combine_text_under_n_chars=0,
        new_after_n_chars=50,
        max_characters=100,
    )
    elements = partition_html(filename)
    chunks = chunk_by_title(
        elements,
        combine_text_under_n_chars=0,
        new_after_n_chars=50,
        max_characters=100,
    )

    for chunk in chunks:
        assert isinstance(chunk, Text)
        assert len(chunk.text) <= 100
    for chunk_element in chunk_elements:
        assert isinstance(chunk_element, Text)
        assert len(chunk_element.text) <= 100
    assert chunk_elements != elements
    assert chunk_elements == chunks


def test_chunk_by_title_drops_detection_class_prob():
    elements: list[Element] = [
        Title(
            "A Great Day",
            metadata=ElementMetadata(
                detection_class_prob=0.5,
            ),
        ),
        Text(
            "Today is a great day.",
            metadata=ElementMetadata(
                detection_class_prob=0.62,
            ),
        ),
        Text(
            "It is sunny outside.",
            metadata=ElementMetadata(
                detection_class_prob=0.73,
            ),
        ),
        Title(
            "An Okay Day",
            metadata=ElementMetadata(
                detection_class_prob=0.84,
            ),
        ),
        Text(
            "Today is an okay day.",
            metadata=ElementMetadata(
                detection_class_prob=0.95,
            ),
        ),
    ]
    chunks = chunk_by_title(elements, combine_text_under_n_chars=0)
    assert str(chunks[0]) == str(
        CompositeElement("A Great Day\n\nToday is a great day.\n\nIt is sunny outside."),
    )
    assert str(chunks[1]) == str(CompositeElement("An Okay Day\n\nToday is an okay day."))


def test_chunk_by_title_drops_extra_metadata():
    elements: list[Element] = [
        Title(
            "A Great Day",
            metadata=ElementMetadata(
                coordinates=CoordinatesMetadata(
                    points=(
                        (0.1, 0.1),
                        (0.2, 0.1),
                        (0.1, 0.2),
                        (0.2, 0.2),
                    ),
                    system=CoordinateSystem(width=0.1, height=0.1),
                ),
            ),
        ),
        Text(
            "Today is a great day.",
            metadata=ElementMetadata(
                coordinates=CoordinatesMetadata(
                    points=(
                        (0.2, 0.2),
                        (0.3, 0.2),
                        (0.2, 0.3),
                        (0.3, 0.3),
                    ),
                    system=CoordinateSystem(width=0.2, height=0.2),
                ),
            ),
        ),
        Text(
            "It is sunny outside.",
            metadata=ElementMetadata(
                coordinates=CoordinatesMetadata(
                    points=(
                        (0.3, 0.3),
                        (0.4, 0.3),
                        (0.3, 0.4),
                        (0.4, 0.4),
                    ),
                    system=CoordinateSystem(width=0.3, height=0.3),
                ),
            ),
        ),
        Title(
            "An Okay Day",
            metadata=ElementMetadata(
                coordinates=CoordinatesMetadata(
                    points=(
                        (0.3, 0.3),
                        (0.4, 0.3),
                        (0.3, 0.4),
                        (0.4, 0.4),
                    ),
                    system=CoordinateSystem(width=0.3, height=0.3),
                ),
            ),
        ),
        Text(
            "Today is an okay day.",
            metadata=ElementMetadata(
                coordinates=CoordinatesMetadata(
                    points=(
                        (0.4, 0.4),
                        (0.5, 0.4),
                        (0.4, 0.5),
                        (0.5, 0.5),
                    ),
                    system=CoordinateSystem(width=0.4, height=0.4),
                ),
            ),
        ),
    ]

    chunks = chunk_by_title(elements, combine_text_under_n_chars=0)

    assert str(chunks[0]) == str(
        CompositeElement("A Great Day\n\nToday is a great day.\n\nIt is sunny outside."),
    )

    assert str(chunks[1]) == str(CompositeElement("An Okay Day\n\nToday is an okay day."))


def test_it_considers_separator_length_when_pre_chunking():
    """PreChunker includes length of separators when computing remaining space."""
    elements: list[Element] = [
        Title("Chunking Priorities"),  # 19 chars
        ListItem("Divide text into manageable chunks"),  # 34 chars
        ListItem("Preserve semantic boundaries"),  # 28 chars
        ListItem("Minimize mid-text chunk-splitting"),  # 33 chars
    ]  # 114 chars total but 120 chars with separators

    chunks = chunk_by_title(elements, max_characters=115)

    assert chunks == [
        CompositeElement(
            "Chunking Priorities"
            "\n\nDivide text into manageable chunks"
            "\n\nPreserve semantic boundaries",
        ),
        CompositeElement("Minimize mid-text chunk-splitting"),
    ]


# ================================================================================================
# UNIT-TESTS
# ================================================================================================
# These test individual components in isolation so can exercise all edge cases while still
# performing well.
# ================================================================================================


class Describe_chunk_by_title:
    """Unit-test suite for `unstructured.chunking.title.chunk_by_title()` function."""

    @pytest.mark.parametrize(
        ("kwargs", "expected_value"),
        [
            ({"include_orig_elements": True}, True),
            ({"include_orig_elements": False}, False),
            ({"include_orig_elements": None}, True),
            ({}, True),
        ],
    )
    def it_supports_the_include_orig_elements_option(
        self, kwargs: dict[str, Any], expected_value: bool, _chunk_by_title_: Mock
    ):
        # -- this line would raise if "include_orig_elements" was not an available parameter on
        # -- `chunk_by_title()`.
        chunk_by_title([], **kwargs)

        _, opts = _chunk_by_title_.call_args.args
        assert opts.include_orig_elements is expected_value

    # -- fixtures --------------------------------------------------------------------------------

    @pytest.fixture()
    def _chunk_by_title_(self, request: FixtureRequest):
        return function_mock(request, "unstructured.chunking.title._chunk_by_title")


class Describe_ByTitleChunkingOptions:
    """Unit-test suite for `unstructured.chunking.title._ByTitleChunkingOptions` objects."""

    @pytest.mark.parametrize("n_chars", [-1, -42])
    def it_rejects_combine_text_under_n_chars_for_n_less_than_zero(self, n_chars: int):
        with pytest.raises(
            ValueError,
            match=f"'combine_text_under_n_chars' argument must be >= 0, got {n_chars}",
        ):
            _ByTitleChunkingOptions.new(combine_text_under_n_chars=n_chars)

    def it_accepts_0_for_combine_text_under_n_chars_to_disable_chunk_combining(self):
        """Specifying `combine_text_under_n_chars=0` is how a caller disables chunk-combining."""
        opts = _ByTitleChunkingOptions(combine_text_under_n_chars=0)
        assert opts.combine_text_under_n_chars == 0

    def it_does_not_complain_when_specifying_combine_text_under_n_chars_by_itself(self):
        """Caller can specify `combine_text_under_n_chars` arg without specifying other options."""
        try:
            opts = _ByTitleChunkingOptions(combine_text_under_n_chars=50)
        except ValueError:
            pytest.fail("did not accept `combine_text_under_n_chars` as option by itself")

        assert opts.combine_text_under_n_chars == 50

    @pytest.mark.parametrize(
        ("combine_text_under_n_chars", "max_characters", "expected_hard_max"),
        [(600, None, 500), (600, 450, 450)],
    )
    def it_rejects_combine_text_under_n_chars_greater_than_maxchars(
        self, combine_text_under_n_chars: int, max_characters: Optional[int], expected_hard_max: int
    ):
        """`combine_text_under_n_chars` > `max_characters` can produce behavior confusing to users.

        The behavior is no different from `combine_text_under_n_chars == max_characters`, but if
        `max_characters` is left to default (500) and `combine_text_under_n_chars` is set to a
        larger number like 1500 then it can look like chunk-combining isn't working.
        """
        with pytest.raises(
            ValueError,
            match=(
                "'combine_text_under_n_chars' argument must not exceed `max_characters` value,"
                f" got {combine_text_under_n_chars} > {expected_hard_max}"
            ),
        ):
            _ByTitleChunkingOptions.new(
                max_characters=max_characters, combine_text_under_n_chars=combine_text_under_n_chars
            )

    def it_does_not_complain_when_specifying_new_after_n_chars_by_itself(self):
        """Caller can specify `new_after_n_chars` arg without specifying any other options."""
        try:
            opts = _ByTitleChunkingOptions.new(new_after_n_chars=200)
        except ValueError:
            pytest.fail("did not accept `new_after_n_chars` as option by itself")

        assert opts.soft_max == 200

    @pytest.mark.parametrize(
        ("multipage_sections", "expected_value"),
        [(True, True), (False, False), (None, CHUNK_MULTI_PAGE_DEFAULT)],
    )
    def it_knows_whether_to_break_chunks_on_page_boundaries(
        self, multipage_sections: bool, expected_value: bool
    ):
        opts = _ByTitleChunkingOptions(multipage_sections=multipage_sections)
        assert opts.multipage_sections is expected_value
