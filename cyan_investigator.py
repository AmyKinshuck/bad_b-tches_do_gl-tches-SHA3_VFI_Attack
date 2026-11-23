import csv

# Change this file depending on the csv file you are
file_to_investigate = "WideScanResults_2026-11-23_00-05.csv"

with open("cyan_data_only_3.csv", "w", newline="") as writefile:
    writefile.write("result,delay_ns,length_ns,SHA3output\n")

    with open(file_to_investigate, "r") as readfile:
        data = csv.DictReader(readfile)
        # Initialise empty list to collect cyan data
        cyan_rows = []                                         
        for row in data:
            # Append results of a cyan output glitch to the cyan_rows list
            if row["result"] == "cyan":
                cyan_rows.append(row)                          

     # Sort all cyan glitch results by glitch delay, smallest first
     # This will let us read through our results much more easily
    cyan_rows.sort(key=lambda r: int(r["delay_ns"]))          
    for row in cyan_rows:    
        # Write out the ordered cyan results to a csv file                                   
        writefile.write(",".join(row.values()) + "\n")