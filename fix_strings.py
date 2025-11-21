with open('main.py', 'r') as f:
    lines = f.readlines()

output = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Check if line ends with an opening quote but no closing
    stripped = line.strip()
    if (stripped.endswith('logger.info("') or 
        stripped.endswith('print("') or
        stripped.endswith('logger.info(f"') or
        stripped.endswith('print(f"') or
        stripped.endswith('logger.warning("') or
        stripped.endswith('logger.error("')):
        
        # This is a broken line, join with next
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            # Combine them
            combined = line.rstrip() + '\\n' + next_line.lstrip()
            output.append(combined)
            i += 2
            continue
    
    output.append(line)
    i += 1

with open('main.py', 'w') as f:
    f.writelines(output)

print("Fixed!")
