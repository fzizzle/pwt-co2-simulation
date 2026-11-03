"""Regenerate the approved Study B sweep and separate exploratory extensions.

Run python -m pwt.sensitivity_report; install requirements-study-b.txt first.
"""

from pwt.sensitivity import HERE, export, sensitivity
from pwt.sensitivity_extensions import extensions
from pwt.sensitivity_reporting import MARKER, PANELS, plot, slides, tables_and_findings


def main():
    frame = sensitivity()
    ranked = export(frame)
    extra = extensions()
    for name, selection in PANELS:
        plot(ranked, selection, HERE / f"study-b-{name}.png")
    report = HERE / "study-b-sensitivity.md"
    introduction = report.read_text(encoding="utf-8").split(MARKER)[0].rstrip()
    report.write_text(introduction + "\n\n" + MARKER + "\n\n"
                      + tables_and_findings(frame, ranked, extra) + "\n", encoding="utf-8")
    slides(HERE, frame, ranked)
    print(f"Generated {len(frame)} approved runs, {len(ranked)} spans, all extensions, four paired figures and five slides.")


if __name__ == "__main__":
    main()
