import datetime
import random
import os

# --- Configuration for ANSI Colors (Dependency-free replacement for colorama) ---
class Colors:
    """ANSI color codes for CLI output."""
    RESET = '\033[0m'
    BRIGHT = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

# --- Configuration & Constants ---

# Define the total slots for different vehicle types (Capacity)
MAX_SLOTS = {
    'BIKE': 20,
    'CAR': 30,
    'EV': 10, # Dedicated EV slots
    'HEAVY': 5,
    'VIP': 5  # Reserved VIP slots for CAR/EV
}

# Base Pricing per hour
# Premium Add-on: Vehicle type-based pricing + Variable pricing (First 2 hours fixed)
PRICING = {
    'BIKE': {'FIXED_HOURS': 2, 'FIXED_RATE': 5, 'PER_HOUR': 2},
    'CAR': {'FIXED_HOURS': 2, 'FIXED_RATE': 10, 'PER_HOUR': 5},
    'EV': {'FIXED_HOURS': 2, 'FIXED_RATE': 12, 'PER_HOUR': 6}, # Slightly higher for premium spot/charging
    'HEAVY': {'FIXED_HOURS': 1, 'FIXED_RATE': 15, 'PER_HOUR': 8},
    'VIP': {'FIXED_HOURS': 3, 'FIXED_RATE': 15, 'PER_HOUR': 4} # Discounted per-hour rate for loyalty
}

# --- Global State ---
# Structure: {Slot_ID: {'vehicle_no': str, 'type': str, 'entry_time': datetime.datetime}}
parking_lot = {}
revenue_log = []
total_capacity = sum(MAX_SLOTS.values())

# --- Utility Functions ---

def clear_screen():
    """Clears the console for a clean UI."""
    # Note: On some systems, this might not clear the screen entirely,
    # but it attempts to refresh the display area.
    os.system('cls' if os.name == 'nt' else 'clear')

def generate_slot_id(vehicle_type, index):
    """Generates a structured Slot ID (e.g., C-01, V-03)."""
    prefix = vehicle_type[0].upper()
    if vehicle_type == 'EV':
        prefix = 'E'
    elif vehicle_type == 'HEAVY':
        prefix = 'H'
    elif vehicle_type == 'VIP':
        prefix = 'V'
    return f"{prefix}-{index:02d}"

def initialize_parking_lot():
    """Creates the initial, empty slot dictionary with structured IDs."""
    global parking_lot
    parking_lot = {}
    index_map = {'BIKE': 1, 'CAR': 1, 'EV': 1, 'HEAVY': 1, 'VIP': 1}

    # VIP slots are prioritized and separated
    for _ in range(MAX_SLOTS['VIP']):
        slot_id = generate_slot_id('VIP', index_map['VIP'])
        parking_lot[slot_id] = None
        index_map['VIP'] += 1

    # Standard slots
    for v_type in ['BIKE', 'CAR', 'EV', 'HEAVY']:
        for _ in range(MAX_SLOTS[v_type]):
            slot_id = generate_slot_id(v_type, index_map[v_type])
            parking_lot[slot_id] = None
            index_map[v_type] += 1

    # Shuffle for a non-sequential allocation feel
    shuffled_keys = list(parking_lot.keys())
    random.shuffle(shuffled_keys)
    # Recreate the dictionary to apply the shuffled order while maintaining structure
    temp_lot = {k: parking_lot[k] for k in shuffled_keys}
    parking_lot = temp_lot

def calculate_fee(entry_time, exit_time, vehicle_type):
    """
    Calculates the parking fee using the variable pricing model.
    Time Tracking (entry_time) and Billing Engine (fee calculation).
    """
    duration = exit_time - entry_time
    total_seconds = duration.total_seconds()
    # Round up to the nearest hour for billing
    total_hours = max(1, (total_seconds + 3599) // 3600)

    pricing_scheme = PRICING.get(vehicle_type, PRICING['CAR']) # Default to CAR pricing
    fixed_hours = pricing_scheme['FIXED_HOURS']
    fixed_rate = pricing_scheme['FIXED_RATE']
    per_hour_rate = pricing_scheme['PER_HOUR']

    if total_hours <= fixed_hours:
        fee = fixed_rate
    else:
        # Fee = Fixed Rate + (Remaining hours * Per Hour Rate)
        extra_hours = total_hours - fixed_hours
        fee = fixed_rate + (extra_hours * per_hour_rate)

    return fee, total_hours

def find_available_slot(vehicle_type, is_vip=False):
    """
    Finds the first available slot based on vehicle type and VIP status.
    Premium Add-on: VIP reserved slots and priority entry.
    Slot Allocation.
    """
    # 1. Priority check for VIP slots (for VIP vehicles only)
    if is_vip:
        for slot_id, status in parking_lot.items():
            if slot_id.startswith('V-') and status is None:
                return slot_id, 'VIP'

    # 2. Check for type-specific slots
    type_prefix = vehicle_type[0].upper()
    if vehicle_type == 'EV': type_prefix = 'E'
    elif vehicle_type == 'HEAVY': type_prefix = 'H'

    for slot_id, status in parking_lot.items():
        if slot_id.startswith(f'{type_prefix}-') and status is None:
            return slot_id, vehicle_type

    # 3. Fallback: Check for any open 'CAR' or 'VIP' slot (for CAR/EV if type-specific is full)
    if vehicle_type in ['CAR', 'EV']:
        for slot_id, status in parking_lot.items():
            # Allow CAR/EV to spill over into standard CAR slots or VIP slots
            if (slot_id.startswith('C-') or slot_id.startswith('V-')) and status is None:
                # Note: We still store the original vehicle_type ('CAR' or 'EV')
                # If it's a VIP slot, we treat it as a CAR-type for general allocation here
                return slot_id, parking_lot.get(slot_id, {}).get('type', vehicle_type)

    # 4. General fallback (e.g., BIKE in a CAR slot if allowed, but keeping it simple here)
    # The current structured allocation is strict by design for better management.
    return None, None

# --- Core Management Functions ---

def vehicle_entry(vehicle_no, vehicle_type, is_vip=False):
    """Handles vehicle entry and slot assignment."""
    vehicle_type = vehicle_type.upper()
    vehicle_no = vehicle_no.upper()

    if vehicle_type not in ['BIKE', 'CAR', 'EV', 'HEAVY']:
        print(Colors.RED + "\n[ERROR] Invalid vehicle type. Must be BIKE, CAR, EV, or HEAVY." + Colors.RESET)
        return

    # Validation: Check if vehicle is already parked
    for slot_id, info in parking_lot.items():
        if info and info['vehicle_no'] == vehicle_no:
            print(Colors.YELLOW + f"\n[WARN] Vehicle {vehicle_no} is already parked in Slot {slot_id}." + Colors.RESET)
            return

    # Find the slot
    slot_id, allocated_type = find_available_slot(vehicle_type, is_vip)

    if slot_id:
        entry_time = datetime.datetime.now()
        parking_lot[slot_id] = {
            'vehicle_no': vehicle_no,
            'type': vehicle_type,
            'entry_time': entry_time,
            'is_vip': is_vip
        }
        status_color = Colors.CYAN if is_vip else Colors.GREEN
        print(status_color + Colors.BRIGHT + f"\n[SUCCESS] Vehicle {vehicle_no} ({vehicle_type}) entered." + Colors.RESET)
        print(status_color + f"Allocated Slot: {slot_id} | Entry Time: {entry_time.strftime('%Y-%m-%d %H:%M:%S')}" + Colors.RESET)
    else:
        print(Colors.RED + "\n[FAILURE] Parking lot is full for the requested vehicle type." + Colors.RESET)

def vehicle_exit(vehicle_no):
    """Handles vehicle exit, fee calculation, and slot freeing."""
    vehicle_no = vehicle_no.upper()

    # Find the vehicle by number
    found_slot_id = None
    for slot_id, info in parking_lot.items():
        if info and info['vehicle_no'] == vehicle_no:
            found_slot_id = slot_id
            break

    # Validation: Check for missing vehicle
    if not found_slot_id:
        print(Colors.RED + f"\n[ERROR] Vehicle {vehicle_no} not found in the parking lot." + Colors.RESET)
        return

    # Process Exit Clearance
    exit_time = datetime.datetime.now()
    info = parking_lot[found_slot_id]
    entry_time = info['entry_time']
    v_type = info['type']

    # Calculate Fee
    fee, total_hours = calculate_fee(entry_time, exit_time, v_type)

    # Log Revenue
    revenue_log.append({
        'vehicle_no': vehicle_no,
        'type': v_type,
        'slot_id': found_slot_id,
        'entry_time': entry_time,
        'exit_time': exit_time,
        'duration_hrs': total_hours,
        'fee': fee
    })

    # Free up the slot
    parking_lot[found_slot_id] = None

    # Display Exit Report
    print(Colors.GREEN + Colors.BRIGHT + f"\n[EXIT REPORT] Vehicle {vehicle_no} Exited from Slot {found_slot_id}" + Colors.RESET)
    print(Colors.GREEN + "--------------------------------------------------------" + Colors.RESET)
    print(Colors.YELLOW + f"  Vehicle Type: {v_type}" + Colors.RESET)
    print(Colors.YELLOW + f"  Duration (Hrs): {total_hours}" + Colors.RESET)
    print(Colors.YELLOW + f"  Total Fee: ${fee:.2f}" + Colors.RESET)
    print(Colors.GREEN + "--------------------------------------------------------" + Colors.RESET)
    print(Colors.MAGENTA + f"  Thank you for parking with us!" + Colors.RESET)


def display_status():
    """Displays the current parking lot occupancy and status."""
    clear_screen()
    print(Colors.BLUE + Colors.BRIGHT + "=======================================================" + Colors.RESET)
    print(Colors.BLUE + Colors.BRIGHT + "         SMART PARKING LOT STATUS DASHBOARD            " + Colors.RESET)
    print(Colors.BLUE + Colors.BRIGHT + "=======================================================" + Colors.RESET)

    occupied_count = sum(1 for status in parking_lot.values() if status is not None)
    available_count = total_capacity - occupied_count
    utilization = (occupied_count / total_capacity) * 100 if total_capacity else 0

    print(Colors.CYAN + f"Total Capacity: {total_capacity} | Occupied: {occupied_count} | Available: {available_count}" + Colors.RESET)
    print(Colors.CYAN + f"Utilization: {utilization:.2f}%" + Colors.RESET)
    print("-" * 55)

    # Column definitions
    COL_SLOT = 8
    COL_STATUS = 15
    COL_TYPE = 8
    COL_VEHICLE = 20
    
    # Detailed Slot View (Optimized for readability and strict alignment)
    # Header: SLOT     STATUS          TYPE     VEHICLE NO
    header = "{:<{}} {:<{}} {:<{}} {:<{}}".format(
        "SLOT", COL_SLOT, 
        "STATUS", COL_STATUS, 
        "TYPE", COL_TYPE, 
        "VEHICLE NO", COL_VEHICLE
    )
    print(Colors.WHITE + Colors.BRIGHT + header + Colors.RESET)
    print(Colors.WHITE + "-" * (COL_SLOT + COL_STATUS + COL_TYPE + COL_VEHICLE + 3) + Colors.RESET) # 3 for separators

    # Sort slots by ID for easier visual tracking (e.g., B-01, B-02, C-01, V-01)
    sorted_slots = sorted(parking_lot.items(), key=lambda item: item[0])

    for slot_id, info in sorted_slots:
        if info:
            v_type = info['type']
            v_no = info['vehicle_no']
            is_vip = info.get('is_vip', False)

            # Determine status and color
            if is_vip:
                status_text = "OCCUPIED (VIP)"
                status_color = Colors.MAGENTA
                type_color = Colors.MAGENTA
            else:
                status_text = "OCCUPIED"
                status_color = Colors.RED
                if v_type == 'EV':
                    type_color = Colors.GREEN
                elif v_type == 'BIKE':
                    type_color = Colors.CYAN
                else:
                    type_color = Colors.YELLOW
            
            # Use fixed width formatting for data fields
            line = "{:<{}} {}{:<{}}{} {:<{}} {:<{}}".format(
                slot_id, COL_SLOT,
                status_color, status_text, COL_STATUS, Colors.RESET, # Apply color within formatting block for accurate width
                type_color + v_type + Colors.RESET, COL_TYPE,
                Colors.WHITE + v_no + Colors.RESET, COL_VEHICLE
            )
            print(line)
        else:
            # Determine the original intended type for the empty slot for context
            intended_type = 'UNKNOWN'
            if slot_id.startswith('B-'): intended_type = 'BIKE'
            elif slot_id.startswith('C-'): intended_type = 'CAR'
            elif slot_id.startswith('E-'): intended_type = 'EV'
            elif slot_id.startswith('H-'): intended_type = 'HEAVY'
            elif slot_id.startswith('V-'): intended_type = 'VIP'
            
            # Available Slot Formatting
            line = "{:<{}} {}{:<{}}{} {:<{}} {:<{}}".format(
                Colors.WHITE + slot_id + Colors.RESET, COL_SLOT,
                Colors.GREEN, "AVAILABLE", COL_STATUS, Colors.RESET,
                Colors.RESET + intended_type, COL_TYPE,
                "", COL_VEHICLE
            )
            print(line)
    print("-" * 55)

def display_daily_report():
    """Generates and displays the Daily Revenue Report."""
    clear_screen()
    print(Colors.BLUE + Colors.BRIGHT + "=======================================================" + Colors.RESET)
    print(Colors.BLUE + Colors.BRIGHT + "            DAILY REVENUE REPORT                       " + Colors.RESET)
    print(Colors.BLUE + Colors.BRIGHT + "=======================================================" + Colors.RESET)

    if not revenue_log:
        print(Colors.YELLOW + "No transactions recorded yet for the day." + Colors.RESET)
        print("-" * 55)
        return

    total_revenue = sum(item['fee'] for item in revenue_log)
    total_vehicles = len(revenue_log)
    avg_duration = sum(item['duration_hrs'] for item in revenue_log) / total_vehicles if total_vehicles else 0

    print(Colors.GREEN + f"Total Revenue Earned: {Colors.GREEN + Colors.BRIGHT}${total_revenue:.2f}" + Colors.RESET)
    print(Colors.GREEN + f"Total Vehicles Processed: {total_vehicles}" + Colors.RESET)
    print(Colors.GREEN + f"Average Parking Duration: {avg_duration:.1f} hours" + Colors.RESET)
    print("-" * 55)

    # Column definitions for report
    COL_SLOT = 8
    COL_VEHICLE_REPORT = 12
    COL_TYPE_REPORT = 8
    COL_DURATION = 10
    COL_FEE = 10
    
    # Detailed Transaction List Header: SLOT     VEHICLE    TYPE     DURATION   FEE
    header = "{:<{}} {:<{}} {:<{}} {:<{}} {:<{}}".format(
        "SLOT", COL_SLOT, 
        "VEHICLE", COL_VEHICLE_REPORT, 
        "TYPE", COL_TYPE_REPORT, 
        "DURATION", COL_DURATION, 
        "FEE", COL_FEE
    )
    print(Colors.WHITE + Colors.BRIGHT + header + Colors.RESET)
    print(Colors.WHITE + "-" * (COL_SLOT + COL_VEHICLE_REPORT + COL_TYPE_REPORT + COL_DURATION + COL_FEE + 4) + Colors.RESET) # 4 for separators

    for record in revenue_log:
        # Data rows for report
        print("{:<{}} {:<{}} {:<{}} {:<{}.1f} {:<{}.2f}".format(
            record['slot_id'], COL_SLOT,
            record['vehicle_no'], COL_VEHICLE_REPORT,
            record['type'], COL_TYPE_REPORT,
            record['duration_hrs'], COL_DURATION,
            record['fee'], COL_FEE
        ))
    print("-" * 55)


# --- Main Application Loop ---

def main_menu():
    """Displays the main CLI menu and handles user input."""
    initialize_parking_lot() # Setup the lot on startup

    while True:
        display_status()
        print(Colors.YELLOW + Colors.BRIGHT + "\n\n--- MENU ---" + Colors.RESET)
        print(Colors.GREEN + "1. Vehicle Entry" + Colors.RESET)
        print(Colors.GREEN + "2. Vehicle Exit" + Colors.RESET)
        print(Colors.GREEN + "3. View Parking Status (Current)" + Colors.RESET)
        print(Colors.GREEN + "4. View Daily Revenue Report" + Colors.RESET)
        print(Colors.RED + "5. Exit System" + Colors.RESET)
        print(Colors.YELLOW + "--------------------------------------" + Colors.RESET)

        try:
            choice = input(Colors.CYAN + "Enter your choice (1-5): " + Colors.WHITE).strip()

            if not choice:
                break

            choice = int(choice)
        except EOFError:
            # Handle non-interactive execution environment closing the input stream
            print(Colors.RED + "\n[SYSTEM] Input stream closed. Exiting gracefully." + Colors.RESET)
            break
        except ValueError:
            print(Colors.RED + "\nInvalid input. Please enter a number between 1 and 5." + Colors.RESET)
            continue

        if choice == 1:
            clear_screen()
            print(Colors.MAGENTA + Colors.BRIGHT + "--- VEHICLE ENTRY ---" + Colors.RESET)
            v_no = input("Enter Vehicle Number: ").strip().upper()
            v_type = input("Enter Vehicle Type (BIKE/CAR/EV/HEAVY): ").strip().upper()
            is_vip_str = input("Is this a VIP/Loyalty Customer? (y/n): ").strip().lower()
            is_vip = is_vip_str == 'y'
            vehicle_entry(v_no, v_type, is_vip)
            
            # --- PAUSE ADDED ---
            try:
                input(Colors.YELLOW + "\nPress Enter to return to menu..." + Colors.RESET)
            except EOFError:
                break
            # -------------------

        elif choice == 2:
            clear_screen()
            print(Colors.MAGENTA + Colors.BRIGHT + "--- VEHICLE EXIT ---" + Colors.RESET)
            v_no = input("Enter Vehicle Number to Exit: ").strip().upper()
            vehicle_exit(v_no)
            
            # --- PAUSE ADDED ---
            try:
                input(Colors.YELLOW + "\nPress Enter to return to menu..." + Colors.RESET)
            except EOFError:
                break
            # -------------------
            
        elif choice == 3:
            # Display status is already called at the start of the loop, but this forces a refresh/view
            display_status()
            
            # --- PAUSE ADDED ---
            try:
                input(Colors.YELLOW + "\nPress Enter to return to menu..." + Colors.RESET)
            except EOFError:
                break
            # -------------------
            
        elif choice == 4:
            display_daily_report()
            
            # --- PAUSE ADDED ---
            try:
                input(Colors.YELLOW + "\nPress Enter to return to menu..." + Colors.RESET)
            except EOFError:
                break
            # -------------------
            
        elif choice == 5:
            clear_screen()
            print(Colors.GREEN + Colors.BRIGHT + "Thank you for using the Smart Parking Management System. Goodbye!" + Colors.RESET)
            break

        else:
            print(Colors.RED + "\nInvalid choice. Please select a valid option (1-5)." + Colors.RESET)


if __name__ == "__main__":
    main_menu()