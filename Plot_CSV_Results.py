import csv
import matplotlib.pyplot as plt

colours = {"cyan":"tab:cyan", "red":"tab:red", "gray":"black",
           "green":"tab:green", "NoGlitchFired":"orange"}

csv_to_plot = WideScan_Results.csv

groups = {}
with open(file=csv_to_plot, newline="") as fh:
    reader = csv.DictReader(fh)          # reads the header row automatically
    fields = reader.fieldnames

    # Find each column by name, wherever it sits
    delay_col  = next(c for c in fields if "delay"  in c.lower())
    length_col = next(c for c in fields if "length" in c.lower())
    result_col = next(c for c in fields if "result" in c.lower()
                                        or "colour" in c.lower()
                                        or "color"  in c.lower())

    for row in reader:
        try:
            delay  = int(row[delay_col])
            length = int(row[length_col])
        except (ValueError, TypeError):
            continue                     # skip any malformed line
        classification = row[result_col].strip()

        g = groups.setdefault(classification, ([], []))
        g[0].append(delay)
        g[1].append(length)

for name in [ "gray", "green", "cyan", "red"]:
    if name in groups:
        x, y = groups[name]
        plt.scatter(x, y, c=colours.get(name, "purple"), s=6, label=name)

plt.xlabel("Glitch delay (ns)")
plt.ylabel("Glitch length (ns)")
plt.title("Glitch parameter map")
plt.legend()
plt.show()