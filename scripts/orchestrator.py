#!/usr/bin/env python3
import sys
import re
import os

def usage():
    print("Usage: orchestrator.py <command> [args]")
    print("Commands:")
    print("  check-active")
    print("  extract-bugfix <review_file_path>")
    print("  inject-bugfix <bugfix_file_path>")
    print("  mark-bugfix-complete")
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        usage()
        
    cmd = sys.argv[1]
    plan_path = os.environ.get("IMPL_PLAN", "implementation_plan.md")
    
    if cmd == "check-active":
        with open(plan_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if re.search(r'(🔒\s*LOCKED|💻\s*EXECUTING|🐛\s*BUGFIX PLANNED)', content):
            sys.exit(0)
        else:
            sys.exit(1)
            
    elif cmd == "extract-bugfix":
        if len(sys.argv) < 3:
            usage()
        review_path = sys.argv[2]
        try:
            with open(review_path, 'r', encoding='utf-8') as f:
                review_content = f.read()
        except FileNotFoundError:
            sys.exit(1)
            
        # Match from "## Bugfix Plan" to the next "## " heading or "---"
        match = re.search(r'(?i)(###?\s*(?:🐛\s*)?Bugfix Plan.*?)(?=###?\s*End of Bugfix Plan|(?:\n---)|\n##\s|$)', review_content, re.DOTALL)
        if match:
            print(match.group(1).strip())
            sys.exit(0)
        else:
            sys.exit(1)

    elif cmd == "inject-bugfix":
        if len(sys.argv) < 3:
            usage()
        bugfix_file = sys.argv[2]
        with open(bugfix_file, 'r', encoding='utf-8') as f:
            bugfix_content = f.read().strip()
            
        # Strip heading if present so we can standardise it
        bugfix_content = re.sub(r'(?i)^###?\s*(?:🐛\s*)?Bugfix Plan\s*\n', '', bugfix_content).strip()
            
        with open(plan_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        in_active_phase = False
        new_lines = []
        i = 0
        in_stale_bugfix = False
        injected = False
        
        status_regex = re.compile(r'(.*)(🔒\s*LOCKED|💻\s*EXECUTING|🐛\s*BUGFIX PLANNED)(.*)')
        
        while i < len(lines):
            line = lines[i]
            
            if line.startswith("## ") and not "Bugfix Plan" in line and not "🐛" in line:
                in_active_phase = False
                in_stale_bugfix = False
                
            match = status_regex.search(line)
            if match and not in_active_phase and not injected:
                in_active_phase = True
                line = status_regex.sub(r'\1🐛 BUGFIX PLANNED\3', line)
                new_lines.append(line)
                new_lines.append('\n')
                new_lines.append('## 🐛 Bugfix Plan\n\n')
                new_lines.append(bugfix_content + '\n\n')
                injected = True
                i += 1
                continue
                
            if in_active_phase and ("Bugfix Plan" in line or "🐛" in line) and line.startswith("##"):
                in_stale_bugfix = True
                i += 1
                continue
                
            if in_stale_bugfix:
                if line.startswith("## ") or line.startswith("---"):
                    in_stale_bugfix = False
                else:
                    i += 1
                    continue
                    
            new_lines.append(line)
            i += 1
            
        if not injected:
            print("Error: Could not find active phase to inject bugfix.", file=sys.stderr)
            sys.exit(1)
            
        with open(plan_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
            
    elif cmd == "mark-bugfix-complete":
        with open(plan_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content, count = re.subn(r'(🐛\s*BUGFIX PLANNED)', r'✅ EXECUTION COMPLETE', content, count=1)
        if count == 0:
            print("Error: Could not find BUGFIX PLANNED status to mark complete.", file=sys.stderr)
            sys.exit(1)
            
        with open(plan_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
    else:
        print(f"Unknown command: {cmd}")
        usage()

if __name__ == "__main__":
    main()
