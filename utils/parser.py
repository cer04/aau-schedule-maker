import re
import docx
import pdfplumber
import datetime
import unicodedata
from docx import Document

def parse_exams_docx(file_path):
    """
    Parses the Exam Schedule (Word). Returns a list of exams.
    """
    results = []
    
    try:
        doc = Document(file_path)
    except Exception as e:
        print(f"Error opening Word file: {e}")
        return results

    # Keywords to identify columns
    header_keywords = {
        "course_name": ["اسم المقرر", "المادة", "المساق"],
        "course_code": ["رمز المقرر", "رقم المادة"],
        "time": ["الوقت", "الزمن", "ساعة الامتحان"],
        "room": ["القاعة", "المكان", "القاعة/ المختبر"],
        "days": ["الأيام", "اليوم", "موعد الامتحان"],
        "section": ["الشعبة", "رقم الشعبة"]
    }

    for table_idx, table in enumerate(doc.tables):
        # Convert table to list of lists
        table_data = []
        for row in table.rows:
            row_data = [cell.text.strip() for cell in row.cells]
            table_data.append(row_data)
        
        if not table_data:
            continue

        # Find Header Row
        header_idx = -1
        col_map = {}
        
        for i, row in enumerate(table_data):
            temp_map = {}
            for col_idx, cell_text in enumerate(row):
                for key, keywords in header_keywords.items():
                    if any(k in cell_text for k in keywords):
                        temp_map[key] = col_idx
                        break
            
            if "time" in temp_map and ("course_name" in temp_map or "days" in temp_map):
                header_idx = i
                col_map = temp_map
                break
        
        if header_idx != -1:
            for row_idx in range(header_idx + 1, len(table_data)):
                row = table_data[row_idx]
                if not row or all(c == "" for c in row):
                    continue
                
                try:
                    time_str = row[col_map["time"]] if "time" in col_map else ""
                    if not time_str or len(time_str) < 3: continue
                        
                    course_name = row[col_map["course_name"]] if "course_name" in col_map else "Unknown Course"
                    days_str = row[col_map["days"]] if "days" in col_map else ""
                    room = row[col_map["room"]] if "room" in col_map else ""
                    section = row[col_map["section"]] if "section" in col_map else ""
                    
                    parsed = parse_time_slot(time_str, days_str_fallback=days_str, is_exam=True)
                    
                    for slot in parsed:
                        results.append({
                            "course_name": course_name,
                            "raw_time": time_str,
                            "start": slot["start"],
                            "end": slot["end"],
                            "date": slot.get("date", ""),
                            "day_of_week": None,  # Let check_availability determine from date
                            "room": room,
                            "section": section
                        })
                except IndexError:
                    continue
    return results

def parse_doctors_pdf(pdf_path):
    """
    Parses the Master Doctor Schedule (PDF). Returns { "Dr. Name": { "busy_slots": { "Mon": [(start, end)] } } }
    """
    doctors = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            
            # 1. Extract Name
            # The PDF text might be reversed (Right-to-Left characters stored Left-to-Right)
            # We will try to find the name in both raw and reversed forms.
            
            lines = text.split('\n')
            found_name = None
            
            for line in lines:
                # cleanup
                line = line.strip()
                if not line: continue

                # Normalize Arabic Presentation Forms (to standard) (NFKC)
                line = unicodedata.normalize('NFKC', line)

                # Remove Tatweels (Arabic elongation char)
                line = re.sub(r'\u0640', '', line)
                
                # Check Normal
                if "المحاضر" in line:
                    # Regex for normal "المحاضر : Name"
                    match = re.search(r"المحاضر\s*[:\-]?\s*(?P<name>.*?)\s*(?::|الرتبة|عبء|\n|$)", line)
                    if match:
                        found_name = match.group("name").strip()
                        break
                
                # Check Reversed
                rev_line = line[::-1]
                if "المحاضر" in rev_line:
                    match = re.search(r"المحاضر\s*[:\-]?\s*(?P<name>.*?)\s*(?::|الرتبة|عبء|\n|$)", rev_line)
                    if match:
                        found_name = match.group("name").strip()
                        break
            
            if found_name:
                name = found_name
            else:
                name = "Unknown Doctor"

            # Normalize name (remove weird chars)
            name = re.sub(r'[^\w\s\u0600-\u06FF]', '', name).strip()
            
            if not name: name = "Unknown Doctor"

            if name not in doctors:
                doctors[name] = {"busy_slots": {d: [] for d in ['Sun', 'Mon', 'Tue', 'Wed', 'Thu']}}
            
            # 2. Extract Table
            table = page.extract_table()
            if not table: continue
            
            # Identify columns
            header_idx = -1
            col_map = {}
            header_keywords = {
                "time": ["الوقت", "الزمن", "ﺖﻗﻮﻟﺍ", "ﻦﻣﺰﻟﺍ"],
                "days": ["الأيام", "اليوم", "ﻡﺎﻳﻷﺍ", "ﻡﻮﻴﻟﺍ"]
            }
            
            for i, row in enumerate(table):
                clean_row = [str(c).strip() if c else "" for c in row]
                temp_map = {}
                for col_idx, cell_text in enumerate(clean_row):
                    for key, keywords in header_keywords.items():
                        if any(k in cell_text for k in keywords):
                            temp_map[key] = col_idx
                            break
                if "time" in temp_map:
                    header_idx = i
                    col_map = temp_map
                    break
            
            if header_idx != -1:
                for row_idx in range(header_idx + 1, len(table)):
                    row = table[row_idx]
                    if not row: continue
                    cleaned_row = [str(c).strip() if c else "" for c in row]
                    
                    try:
                        time_str = cleaned_row[col_map["time"]] if "time" in col_map else ""
                        days_str = cleaned_row[col_map["days"]] if "days" in col_map else ""
                        if not time_str: continue
                        
                        parsed = parse_time_slot(time_str, days_str_fallback=days_str)
                        
                        for slot in parsed:
                            for day in slot['days']:
                                if day in doctors[name]["busy_slots"]:
                                    doctors[name]["busy_slots"][day].append((slot['start'], slot['end']))
                    except Exception:
                        continue
    
    return doctors

def check_availability(exams, doctors_db):
    """
    Matches exams to available doctors.
    """
    debug_first = True  # Only debug first exam
    
    for exam in exams:
        exam_day = exam.get("day_of_week")
        
        # If no day derived from date, try to parse date str to day
        if not exam_day and exam.get("date"):
            try:
                # Date format DD/MM/YYYY
                dt = datetime.datetime.strptime(exam["date"], "%d/%m/%Y")
                # Map python weekday (0=Mon) to our keys
                py_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                # Adjust for our Sun-Thu map
                # 6=Sun, 0=Mon, 1=Tue, 2=Wed, 3=Thu...
                wd = dt.weekday() 
                # Mapping might vary based on system, usually Mon=0
                # Our keys: Sun, Mon, Tue, Wed, Thu
                # Sunday is 6 in Py? Yes.
                if wd == 6: exam_day = "Sun"
                elif wd == 0: exam_day = "Mon"
                elif wd == 1: exam_day = "Tue"
                elif wd == 2: exam_day = "Wed"
                elif wd == 3: exam_day = "Thu"
                else: exam_day = None # Weekend (Fri/Sat)
                
                exam["day_of_week"] = exam_day # Store back
            except ValueError:
                pass
        
        available_docs = []
        
        if not exam_day:
            exam["available_doctors"] = ["Unknown Date/Day"]
            continue

        if debug_first:
            print(f"\n[DEBUG check_availability for first exam]")
            print(f"  Exam day: {exam_day}")
            print(f"  Exam time: {exam['start']} - {exam['end']}")

        start_min = time_to_min(exam["start"])
        end_min = time_to_min(exam["end"])
        
        if debug_first:
            print(f"  Exam minutes: {start_min} - {end_min}")
        
        for doc_name, doc_data in doctors_db.items():
            is_free = True
            busy_on_day = doc_data["busy_slots"].get(exam_day, [])
            
            if debug_first and ("احمد" in doc_name and "عماد" in doc_name):
                print(f"\n  [Checking Dr. Ahmed]")
                print(f"    Doctor: {doc_name[:50]}...")
                print(f"    Busy slots on {exam_day}: {busy_on_day}")
            
            for b_start, b_end in busy_on_day:
                b_s_min = time_to_min(b_start)
                b_e_min = time_to_min(b_end)
                
                # Check Overlap
                # Overlap if (StartA < EndB) and (EndA > StartB)
                if start_min < b_e_min and end_min > b_s_min:
                    is_free = False
                    if debug_first and ("احمد" in doc_name and "عماد" in doc_name):
                        print(f"    Slot {b_start}-{b_end}: OVERLAP! is_free=False")
                    break
                elif debug_first and ("احمد" in doc_name and "عماد" in doc_name):
                    print(f"    Slot {b_start}-{b_end}: No overlap")
            
            if is_free:
                available_docs.append(doc_name)
                if debug_first and ("احمد" in doc_name and "عماد" in doc_name):
                    print(f"    Result: ADDED to available list (WRONG!)")
            elif debug_first and ("احمد" in doc_name and "عماد" in doc_name):
                print(f"    Result: NOT added (correct)")
        
        exam["available_doctors"] = available_docs
        
        if debug_first:
            print(f"\n  Total available: {len(available_docs)}")
            ahmed_in = any("احمد" in d and "عماد" in d for d in available_docs)
            print(f"  Ahmed in list: {ahmed_in}\n")
            debug_first = False  # Only debug first exam
        
    return exams

def time_to_min(t_str):
    try:
        h, m = map(int, t_str.split(':'))
        return h * 60 + m
    except:
        return 0

# Wrapper for backward compatibility or simple direct use
def extract_schedule(file_path):
    # This was the old entry point. 
    # For now, we will assume app.py calls the specific functions depending on inputs.
    # But to prevent breakage if called plainly:
    if file_path.endswith('.docx'):
        return {"exams": parse_exams_docx(file_path)}
    else:
        return {"doctors": parse_doctors_pdf(file_path)} 


def parse_time_slot(time_str, days_str_fallback="", is_exam=False):
    """
    Parses time string. 
    Format seen: "13:00_14:30 , ث" or "( ﻞﻣﺎﻛ ﻲﻫﺎﺟﻭ , ﺙ ,14:30_13:00 )"
    
    IMPORTANT: Cells may contain multiple lines, each representing a different time slot.
    We split by newlines and parse each separately.
    
    Args:
        time_str: The time string to parse
        days_str_fallback: Additional day information
        is_exam: True if parsing exam schedule (uses 12-hour format), False for doctor schedule (24-hour)
    """
    all_results = []
    
    # Split by newlines to handle multi-line cells
    lines = time_str.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Parse this line
        results = _parse_single_time_slot(line, days_str_fallback, is_exam)
        all_results.extend(results)
    
    return all_results

def _parse_single_time_slot(time_str, days_str_fallback="", is_exam=False):
    """
    Internal function to parse a single line of time slot data.
    """
    results = []
    
    # Normalize input
    raw = time_str
    if days_str_fallback:
        raw += " " + days_str_fallback
        
    # Clean up standard chars
    raw = raw.replace('_', '-').replace('–', '-')
    
    # 1. Normalize and check direction
    # If the string looks like "( ... )", it might be reversed if parenthesis are backwards?
    # Actually, in PDF dump: "( ﻞﻣﺎﻛ ﻲﻫﺎﺟﻭ , ﺙ ,14:30_13:00 )"
    # The parenthesis seem correct order physically in the string? "(" at start, ")" at end.
    # But words inside are reversed.
    # The time "14:30_13:00" is also reversed range logic? 
    #   13:00 -> 14:30. "14:30_13:00" means Start=14:30? No.
    #   Usually "Start_End". If visually reversed, might be "End_Start".
    
    # Let's handle generic Time extraction first.
    # Find all HH:MM
    times = re.findall(r'(\d{1,2}:\d{2})', raw)
    
    start_time = "00:00"
    end_time = "00:00"
    
    if len(times) >= 2:
        # We sort them to get Earliest and Latest, assuming standard class block.
        # This avoids conflict with "Start-End" vs "End-Start" ordering unless class crosses midnight.
        t_list = []
        for t in times:
            h, m = map(int, t.split(':'))
            
            # CRITICAL FIX: Detect if this is a PM time in 12-hour format
            # Exam schedules use 12-hour format (1:00 = 1 PM), doctor schedules use 24-hour
            if is_exam and h >= 1 and h <= 6:
                # This is a 12-hour PM time from exam schedule
                # Convert 1:00 -> 13:00, 2:00 -> 14:00, etc.
                h += 12
            
            t_list.append((h, m, f"{h:02d}:{m:02d}"))
        
        t_list.sort() # Sort by hour, then minute
        
        start_time = t_list[0][2]
        end_time = t_list[-1][2]
        
    elif len(times) == 1:
        start_time = times[0]
        end_time = times[0]

    # ... (rest of function)
    elif len(times) == 1:
        start_time = times[0]
        end_time = times[0] # Invalid duration
        
    if start_time == "00:00":
        return []

    # 2. Extract Date (DD/MM/YYYY)
    date_found = ""
    # Look for DD/MM/YYYY or DD-MM-YYYY
    date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', raw)
    if date_match:
        date_found = date_match.group(0)

    # 3. Extract Days
    # Standard English
    found_days = []
    day_map_en = {
        'Sun': ['Sun', 'Sunday', 'Sun.'],
        'Mon': ['Mon', 'Monday', 'Mon.'],
        'Tue': ['Tue', 'Tuesday', 'Tue.'],
        'Wed': ['Wed', 'Wednesday', 'Wed.'],
        'Thu': ['Thu', 'Thursday', 'Thu.']
    }
    
    # Arabic letters/words
    # User clarification: "ث" might be Monday or Tuesday? Standard is Tuesday (Thulatha). 
    # "ن" is Monday (Ithnain). "ر" is Wednesday (Arbia/Rabia).
    # We will map "ث" -> Tue, "ن" -> Mon, "ر" -> Wed, "ح" -> Sun, "خ" -> Thu.
    # We also check for full words.
    
    # Checking raw string for arabic chars
    # We normalized NFKC in checking names, but here we might get raw chars.
    # Let's clean the string of parentheses and comman
    clean_raw = re.sub(r'[(),]', ' ', raw)
    
    # Also create a reversed version of raw to check against
    # Because "Wednesday" might be "ﺭ" or reversed word
    
    for word in clean_raw.split():
        word = word.strip()
        if not word: continue
        # Normalize
        word_norm = unicodedata.normalize('NFKC', word)
        
        # Check standard
        if 'ح' in word_norm or 'الأحد' in word_norm: found_days.append('Sun')
        if 'ن' in word_norm or 'الاثنين' in word_norm or 'الأثنين' in word_norm: found_days.append('Mon')
        if 'ث' in word_norm or 'الثلاثاء' in word_norm: found_days.append('Tue')
        if 'ر' in word_norm or 'الأربعاء' in word_norm or 'الاربعاء' in word_norm: found_days.append('Wed')
        if 'خ' in word_norm or 'الخميس' in word_norm: found_days.append('Thu')
        
        # Check Reversed Word (Common in PDF tables)
        # "الأحد" -> "ﺪﺣﻷﺍ"
        word_rev = word_norm[::-1] 
        # Note: Single letters like 'ن' reversed are just 'ن' (visually same if isolated, but here we handled string reversal earlier?)
        # Actually proper Arabic shaping reversal is complex.
        # But let's check for specific known reversed-chars if simple reverse doesn't work.
        pass # The single letter check above handles 'ن' etc if they are separated.
        
        # If the word is "ﺭ-ﻥ", split failed? 
        # "ﺭ-ﻥ" -> "R-N" -> Wed-Mon.
        # It's likely one token "ﺭ-ﻥ".
        if '-' in word_norm:
            parts = word_norm.split('-')
            for p in parts:
                p = p.strip()
                if 'ح' in p: found_days.append('Sun')
                if 'ن' in p: found_days.append('Mon')
                if 'ث' in p: found_days.append('Tue')
                if 'ر' in p: found_days.append('Wed')
                if 'خ' in p: found_days.append('Thu')
    
    # Deduplicate
    found_days = list(set(found_days))
    
    # Fallback to defaults or Date derived
    if not found_days and date_found:
        # derive from date
        pass # Handled in check_availability

    # If parsing a "General" schedule (like specific date exam), days might be none.
    # But if weekly, we need days.
    
    if not found_days and not date_found:
        # Try finding english days
        for key, arr in day_map_en.items():
            if any(x.lower() in raw.lower() for x in arr):
                found_days.append(key)

    if found_days:
        results.append({
            "start": start_time,
            "end": end_time,
            "days": found_days,
            "date": date_found
        })
    elif date_found:
        # Valid single date event
        results.append({
            "start": start_time,
            "end": end_time,
            "days": [],
            "date": date_found
        })
        
    return results

def calculate_free_time(courses):
    """
    Calculates gaps between 08:00 and 16:00 (standard uni day).
    """
    day_schedule = {d: [] for d in ['Sun', 'Mon', 'Tue', 'Wed', 'Thu']}
    
    for course in courses:
        for day in course['days']:
            if day in day_schedule:
                day_schedule[day].append((course['start'], course['end']))
                
    free_slots_by_day = {}
    
    # Define working hours
    STANDARD_START = 8 * 60
    STANDARD_END = 16 * 60
    
    for day, times in day_schedule.items():
        if not times:
            continue
            
        # Convert to minutes
        time_mins = []
        for start, end in times:
            try:
                s_h, s_m = map(int, start.split(':'))
                e_h, e_m = map(int, end.split(':'))
                time_mins.append((s_h*60 + s_m, e_h*60 + e_m))
            except ValueError:
                continue
            
        # Sort by start time
        time_mins.sort()
        
        if not time_mins:
            continue
            
        merged = []
        curr_start, curr_end = time_mins[0]
        for i in range(1, len(time_mins)):
            next_start, next_end = time_mins[i]
            if next_start < curr_end:
                curr_end = max(curr_end, next_end)
            else:
                merged.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged.append((curr_start, curr_end))
        
        # Calculate gaps
        gaps = []
        last_end = STANDARD_START
        
        for start, end in merged:
            if start > last_end:
                gaps.append((last_end, start))
            last_end = max(last_end, end)
            
        if last_end < STANDARD_END:
            gaps.append((last_end, STANDARD_END))
            
        # Format gaps
        formatted_gaps = []
        for s, e in gaps:
            if e - s >= 15:
                s_str = f"{s//60:02d}:{s%60:02d}"
                e_str = f"{e//60:02d}:{e%60:02d}"
                formatted_gaps.append(f"{s_str} - {e_str}")
        
        if formatted_gaps:
            free_slots_by_day[day] = formatted_gaps

    return free_slots_by_day
