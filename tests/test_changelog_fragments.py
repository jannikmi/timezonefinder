"""The fragment layer must never lose a bullet or reorder a released one.

``scripts/changelog_fragments.py`` sits between every non-exempt change and the
published ``CHANGELOG.rst``. A fragment it silently skips is a change that
reaches a release with no entry, and an assembly that rewrites text below the
unreleased heading is a released version being edited after the fact - neither
announces itself in a diff anybody reads.
"""

import textwrap

import pytest

from scripts.changelog_fragments import (
    CATEGORIES,
    FRAGMENT_ROOT,
    Fragment,
    FragmentError,
    assemble,
    load_fragments,
    render_bullets,
)

FROZEN_CHANGELOG = textwrap.dedent(
    """\
    =========
    Changelog
    =========



    X.X.X (unreleased)
    ------------------

    * a bullet curated before the fragments arrived

    Internal:

    * an internal bullet curated before the fragments arrived


    9.0.0 (2026-09-02)
    ------------------

    * the released text, which nothing here may touch
    """
)

EMPTY_UNRELEASED = textwrap.dedent(
    """\
    =========
    Changelog
    =========



    X.X.X (unreleased)
    ------------------


    9.0.0 (2026-09-02)
    ------------------

    * the released text, which nothing here may touch
    """
)


@pytest.fixture
def fragment_dir(tmp_path):
    """A fragment root shaped like the committed one."""
    root = tmp_path / "changelog.d"
    for category in CATEGORIES:
        (root / category).mkdir(parents=True)
        (root / category / ".gitkeep").touch()
    (root / "README.md").write_text("the contract", encoding="utf-8")
    return root


def write(root, category, name, text):
    path = root / category / f"{name}.rst"
    path.write_text(text, encoding="utf-8")
    return path


class TestLoading:
    def test_the_directory_classifies_the_bullet(self, fragment_dir):
        write(fragment_dir, "user", "visible", "a user-visible change")
        write(fragment_dir, "internal", "tooling", "a development-only change")

        fragments = load_fragments(fragment_dir)

        assert [(f.category, f.text) for f in fragments] == [
            ("user", "a user-visible change"),
            ("internal", "a development-only change"),
        ]

    def test_ordering_is_deterministic_and_independent_of_the_filesystem(
        self, fragment_dir
    ):
        for name in ("zulu", "alpha", "mike"):
            write(fragment_dir, "user", name, f"the {name} change")
        write(fragment_dir, "internal", "alpha-internal", "an internal change")

        fragments = load_fragments(fragment_dir)

        assert [f.path.stem for f in fragments] == [
            "alpha",
            "mike",
            "zulu",
            "alpha-internal",
        ]
        # user before internal, whatever the names sort to
        assert [f.category for f in fragments] == ["user"] * 3 + ["internal"]

    def test_an_absent_root_holds_no_fragments(self, tmp_path):
        assert load_fragments(tmp_path / "nothing-here") == []

    def test_the_keep_file_is_not_a_fragment(self, fragment_dir):
        assert load_fragments(fragment_dir) == []

    @pytest.mark.parametrize(
        "text, message",
        [
            ("", "empty fragment"),
            ("   \n\n  \n", "empty fragment"),
            ("first paragraph\n\nsecond paragraph", "exactly one bullet"),
            ("a change\nwrapped across lines", "exactly one bullet"),
            ("* a change carrying its own marker", "the '\\* ' marker is added"),
        ],
    )
    def test_a_malformed_fragment_is_refused(self, fragment_dir, text, message):
        write(fragment_dir, "user", "broken", text)

        with pytest.raises(FragmentError, match=message):
            load_fragments(fragment_dir)

    @pytest.mark.parametrize(
        "name",
        ["Feature", "feature_name", "feature name", "feature--name", "-feature", "f."],
    )
    def test_a_name_that_is_not_a_kebab_case_slug_is_refused(self, fragment_dir, name):
        """The contract promises kebab-case, so the loader has to require it.

        Not only tidiness: two names differing solely in case are two fragments
        on Linux and one file on macOS or Windows, so a checkout there silently
        loses a bullet - a changelog entry disappearing on someone else's
        filesystem is exactly the failure nothing downstream would report.
        """
        write(fragment_dir, "user", name, "a change")

        with pytest.raises(FragmentError, match="kebab-case slug"):
            load_fragments(fragment_dir)

    def test_a_kebab_case_slug_is_accepted(self, fragment_dir):
        write(fragment_dir, "user", "a-perfectly-fine-slug-2", "a change")

        assert [f.path.stem for f in load_fragments(fragment_dir)] == [
            "a-perfectly-fine-slug-2"
        ]

    def test_a_fragment_that_is_not_rst_is_refused(self, fragment_dir):
        (fragment_dir / "user" / "notes.md").write_text("a change", encoding="utf-8")

        with pytest.raises(FragmentError, match="must end in .rst"):
            load_fragments(fragment_dir)

    def test_an_unclassified_fragment_is_refused(self, fragment_dir):
        (fragment_dir / "loose.rst").write_text("a change", encoding="utf-8")

        with pytest.raises(FragmentError, match="unclassified fragment"):
            load_fragments(fragment_dir)

    def test_an_unknown_category_directory_is_refused(self, fragment_dir):
        (fragment_dir / "maybe").mkdir()

        with pytest.raises(FragmentError, match="unknown category directory"):
            load_fragments(fragment_dir)

    def test_one_slug_may_not_be_filed_under_both_categories(self, fragment_dir):
        write(fragment_dir, "user", "same-change", "described for users")
        write(fragment_dir, "internal", "same-change", "described for contributors")

        with pytest.raises(FragmentError, match="name the same change"):
            load_fragments(fragment_dir)


class TestAssembly:
    def test_fragments_land_in_the_list_their_directory_names(self, fragment_dir):
        write(fragment_dir, "user", "visible", "a user-visible change")
        write(fragment_dir, "internal", "tooling", "a development-only change")

        assembled = assemble(FROZEN_CHANGELOG, load_fragments(fragment_dir))

        unreleased, released = assembled.split("9.0.0 (2026-09-02)")
        main, internal = unreleased.split("Internal:")
        assert "* a user-visible change" in main
        assert "* a development-only change" in internal
        assert "* a user-visible change" not in internal

    def test_assembling_leaves_every_existing_line_byte_identical(self, fragment_dir):
        """The migration property: a frozen baseline is appended to, not rewritten."""
        write(fragment_dir, "user", "visible", "a user-visible change")
        write(fragment_dir, "internal", "tooling", "a development-only change")

        assembled = assemble(FROZEN_CHANGELOG, load_fragments(fragment_dir))

        before = [line for line in FROZEN_CHANGELOG.splitlines() if line.strip()]
        after = [line for line in assembled.splitlines() if line.strip()]
        # every baseline line survives, unmodified and in its original order
        remaining = iter(after)
        assert all(line in remaining for line in before)

    def test_no_fragments_leaves_the_changelog_alone(self):
        assert assemble(FROZEN_CHANGELOG, []) == FROZEN_CHANGELOG

    def test_released_sections_are_never_touched(self, fragment_dir):
        write(fragment_dir, "user", "visible", "a user-visible change")

        assembled = assemble(FROZEN_CHANGELOG, load_fragments(fragment_dir))

        released = assembled[assembled.index("9.0.0 (2026-09-02)") :]
        assert (
            released == FROZEN_CHANGELOG[FROZEN_CHANGELOG.index("9.0.0 (2026-09-02)") :]
        )

    def test_an_internal_marker_is_created_when_the_section_has_none(
        self, fragment_dir
    ):
        write(fragment_dir, "internal", "tooling", "a development-only change")

        assembled = assemble(EMPTY_UNRELEASED, load_fragments(fragment_dir))

        assert "Internal:\n\n* a development-only change" in assembled
        assert assembled.count("Internal:") == 1

    def test_an_empty_section_takes_user_bullets_without_an_internal_marker(
        self, fragment_dir
    ):
        write(fragment_dir, "user", "visible", "a user-visible change")

        assembled = assemble(EMPTY_UNRELEASED, load_fragments(fragment_dir))

        assert "* a user-visible change" in assembled
        assert "Internal:" not in assembled

    def test_a_changelog_without_an_unreleased_section_is_refused(self, fragment_dir):
        write(fragment_dir, "user", "visible", "a user-visible change")

        with pytest.raises(FragmentError, match="no 'X.X.X \\(unreleased\\)' section"):
            assemble("=========\nChangelog\n=========\n", load_fragments(fragment_dir))

    def test_the_result_is_valid_rst_the_next_assembly_can_read(self, fragment_dir):
        """Assembly is repeatable: its own output is a legal input."""
        write(fragment_dir, "user", "first", "the first change")
        once = assemble(EMPTY_UNRELEASED, load_fragments(fragment_dir))

        (fragment_dir / "user" / "first.rst").unlink()
        write(fragment_dir, "user", "second", "the second change")
        twice = assemble(once, load_fragments(fragment_dir))

        assert "* the first change" in twice
        assert "* the second change" in twice
        assert twice.index("the first change") < twice.index("the second change")


def test_render_bullets_adds_the_marker_the_fragment_may_not_carry():
    fragments = [
        Fragment("user", FRAGMENT_ROOT / "user" / "a.rst", "a change"),
        Fragment("internal", FRAGMENT_ROOT / "internal" / "b.rst", "another change"),
    ]

    assert render_bullets(fragments, "user") == ["* a change"]
    assert render_bullets(fragments, "internal") == ["* another change"]


def test_the_committed_fragments_are_sound():
    """The gate this repository actually runs: whatever is filed must assemble."""
    fragments = load_fragments()

    assembled = assemble(
        (FRAGMENT_ROOT.parent / "CHANGELOG.rst").read_text(encoding="utf-8"), fragments
    )
    assert assembled.startswith("=========\nChangelog\n=========")
    for fragment in fragments:
        assert f"* {fragment.text}" in assembled
