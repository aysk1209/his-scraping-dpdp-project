"""Demo: the HIS is updated; the staff assistant keeps up, and says what it cannot.

    python scripts/check_ui_update.py                        # the fixture, before and after a release
    python scripts/check_ui_update.py --before OLD.json --after NEW.json \
        [--control-alias "Close episode=discharge"]          # two crawls of a real portal

The assistant's steps say what to do, never what the screen calls it; the
module, column and button names come from the portal as last crawled. So an
update needs no change to the assistant -- it needs a new crawl. This script
shows that, in five parts:

  1. The portal before (layout v1) is crawled, as every benchmark crawls it.
  2. A vendor release (layout v2) renames and moves every module, splits billing
     in two, moves two fields onto the record page, relabels the headers and
     renames every button. It is crawled with the hospital's alias file -- which
     missed one relabelled header -- and the two crawls are compared.
  3. The same requests, before and after: the instructions re-word themselves.
  4. The two things the release did that nothing could have predicted (a header
     the alias file does not map, a button outside the vocabulary) are withheld,
     with a proposal each -- and the proposals are confirmed, as a super-user
     would, and every task comes back.
  5. What each role hears when they ask "what changed?".

No model anywhere: the comparison is field overlap and string matching, and
every proposal waits for a person.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _present as present                                                    # noqa: E402
from agent import ReplyKind, ScreenMap, Session, StaffRole, compare            # noqa: E402

REPORT = ROOT / "docs" / "benchmark_results" / "ui-update-check.md"

# One request per role whose instructions the release moves somewhere new.
REQUESTS: list[tuple[StaffRole, list[str]]] = [
    (StaffRole.RECEPTION, ["verify insurance for MRN2867825", "POL-44812-K"]),
    (StaffRole.NURSE, ["look up the diagnosis for MRN2867825"]),
    (StaffRole.ADMINISTRATOR, ["discharge MRN2867825 and release the bed"]),
]


def _crawl(layout: str, field_aliases: dict[str, str]):
    from extraction.adapters.mock_his import MockHISDataSource
    from extraction.tier2.browser import PortalBrowser
    from extraction.tier2.navigation import discover
    from tools.mock_portal.serve import BackgroundPortal

    source = MockHISDataSource(records_per_layer=6, seed=42)
    with BackgroundPortal(source, page_size=3, layout=layout) as portal:
        with PortalBrowser(portal.url, portal.username, portal.password,
                           field_aliases=field_aliases) as browser:
            browser.login()
            return discover(browser)


def _ask(role: StaffRole, lines: list[str], screens: ScreenMap) -> str:
    session = Session(role, navigation=screens)
    reply = None
    for line in lines:
        reply = session.respond(line)
    assert reply is not None
    return reply.text


def _indent(text: str, by: str = "    ") -> str:
    return "\n".join(by + line for line in text.split("\n"))


def demo() -> int:
    from tools.mock_portal.layouts import V2_FIELD_ALIASES

    print(present.banner("The HIS is updated -- does the staff assistant keep up?"))

    print(present.rule())
    print("1. Before the update: the portal as every benchmark crawls it (layout v1)")
    before_nav = _crawl("v1", {})
    print(_indent(before_nav.render_table(), "  "))

    print(present.rule())
    print("2. After a vendor release (layout v2), crawled with the hospital's alias file")
    after_nav = _crawl("v2", V2_FIELD_ALIASES)
    before, after = ScreenMap.from_navigation(before_nav), ScreenMap.from_navigation(after_nav)
    changes = compare(before, after)
    print(_indent(changes.render(), ""))

    print(present.rule())
    print("3. The same requests, before and after -- nothing in the assistant was edited")
    for role, lines in REQUESTS:
        print(f"\n  {role.value} > {' / '.join(lines)}")
        for name, screens in (("before", before), ("after", after)):
            print(f"  -- {name}:")
            print(_indent(_ask(role, lines, screens)))

    print(present.rule())
    print("4. A super-user confirms the two proposals; the release is crawled again")
    confirmed_fields = {**V2_FIELD_ALIASES, **changes.field_proposals}
    for header, name in changes.field_proposals.items():
        print(f'  field alias   "{header}" = {name}')
    for label, action in changes.control_proposals.items():
        print(f'  button alias  "{label}" = {action}')
    fixed_nav = _crawl("v2", confirmed_fields)
    fixed = ScreenMap.from_navigation(fixed_nav, changes.control_proposals)
    rechecked = compare(before, fixed)
    statuses = rechecked.by_status()
    print(f"\n  now: {len(statuses['unchanged'])} unchanged, {len(statuses['re-worded'])} re-worded, "
          f"{len(statuses['withheld'])} withheld, of {len(rechecked.impact)} tasks")
    role, lines = REQUESTS[-1]
    print(f"\n  {role.value} > {' / '.join(lines)}")
    print(_indent(_ask(role, lines, fixed)))

    print(present.rule())
    print('5. What each role hears when they ask "what changed?"')
    for role in StaffRole:
        reply = Session(role, navigation=fixed, changes=rechecked).respond("what changed")
        assert reply.kind == ReplyKind.CHANGES
        print(f"\n  {role.value} > what changed")
        print(_indent(reply.text))

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "<!-- Written by scripts/check_ui_update.py: layout v1 against v2 of the fixture portal. -->\n\n"
        + changes.render_markdown()
        + "\n**After the two proposals were confirmed**\n\n"
        + "\n".join(rechecked.render_markdown().split("\n")[-(len(StaffRole) + 4):]),
        encoding="utf-8",
    )
    print()
    print(present.wrote(REPORT))
    print(present.rule())
    print(
        "One crawl re-worded every task the release touched. The two changes nothing could\n"
        "have predicted were withheld, not guessed, each with a proposal a person confirmed.\n"
        "The DPDP gate never moved: the release changed the screens, not who may do what."
    )
    return 0


def compare_files(before_path: Path, after_path: Path, control_aliases: dict[str, str]) -> int:
    from extraction.tier2.navigation import NavigationMap

    before = ScreenMap.from_navigation(
        NavigationMap.model_validate_json(before_path.read_text(encoding="utf-8")), control_aliases)
    after = ScreenMap.from_navigation(
        NavigationMap.model_validate_json(after_path.read_text(encoding="utf-8")), control_aliases)
    print(compare(before, after).render())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--before", type=Path, help="navigation-map.json from the earlier crawl")
    parser.add_argument("--after", type=Path, help="navigation-map.json from the later crawl")
    parser.add_argument("--control-alias", action="append", default=[],
                        help='a confirmed button name, "LABEL=action_id"; repeatable')
    args = parser.parse_args()
    if bool(args.before) != bool(args.after):
        parser.error("--before and --after go together")
    if args.before:
        aliases = dict(a.split("=", 1) for a in args.control_alias)
        return compare_files(args.before, args.after, aliases)
    return demo()


if __name__ == "__main__":
    raise SystemExit(main())
