import mysql.connector
import getpass
import pandas as pd
import random
from datetime import datetime, timedelta


def main():     
    db_password = getpass.getpass()
    
    try: 
        # Connect to the database
        conn = mysql.connector.connect(
            host='mysql.labthreesixfive.com',
            user='bjboulai',
            password= db_password,
            database='bjboulai'
        )
    except mysql.connector.Error as e:
        print("error connecting to mysql", e)
        return
        
    print("Select an option:")
    print("1. Rooms and Rates")
    print("2. Reservations")
    print("3. Reservation Cancellation")
    print("4. Detailed Reservation Information")
    print("5. Revenue")
    print("6. Exit")
    
    # Receive user input
    while True:
        option = input("\nEnter option number: ")

        if option == "1":
            room_rates(conn)
        elif option == "2":
            reservations(conn)
        elif option == "3":
            cancel_res(conn)
        elif option == "4":
            detailed_res_info(conn)
        elif option == "5":
           revenue(conn)
        elif option == "6":
            break
        else:
            print("Invalid option. Please try again.")

    conn.close()


def room_rates(conn):
    cursor = conn.cursor()
    cursor.execute("""
        select r.roomcode, r.roomname,
            round(sum(datediff(res.checkout, res.checkin)) / 180, 2) as PopularityScore,
            mindate as NextAvailableDate,
            max(stay.checkout) as LastStay,
            max(stay.length) as LengthOfStay
        from lab7_rooms r
        left outer join lab7_reservations res on res.room = r.roomcode and
            res.checkin >= date_sub(curdate(), interval 180 day) and
            res.checkout <= curdate()
        join (
            select dates.room, min(potentialdate) as mindate
            from (
                select checkout as potentialdate, room
                from lab7_reservations
                where checkout >= curdate()
                union all
                select curdate() as potentialdate, roomcode as room
                from lab7_rooms
                group by room
            ) as dates
            left outer join lab7_reservations res2 on dates.room = res2.room and
                dates.potentialdate between res2.checkin and date_sub(res2.checkout, interval 1 day)
            where res2.room is null
            group by dates.room
        ) as mindates on mindates.room = r.roomcode
        join (
            select res.room, datediff(res.checkout, res.checkin) as length, res.checkout
            from lab7_reservations res
            where checkout = (select max(checkout) from lab7_reservations res1 where checkout <= curdate() and res.room = res1.room)
        ) as stay on stay.room = r.roomcode
        group by r.roomcode
        order by PopularityScore desc;
    """)

    # Fetch all rows from the result
    rows = cursor.fetchall()

    # Create a DataFrame from the fetched rows
    df = pd.DataFrame(rows, columns=[col[0] for col in cursor.description])

    print(df)
    
    cursor.close()

def reservations(conn):  
    cursor = conn.cursor()
    
    print("Enter reservation details:")
    first_name = input("First name: ")
    last_name = input("Last name: ")
    room_code = input("Room code (or 'Any' for no preference): ")
    bed_type = input("Bed type (or 'Any' for no preference): ")
    begin_date = input("Begin date of stay (YYYY-MM-DD): ")
    end_date = input("End date of stay (YYYY-MM-DD): ")
    num_children = int(input("Number of children: "))
    num_adults = int(input("Number of adults: "))
    total_persons = num_children + num_adults
    
    # check if total_persons is too much for all rooms
    cursor.execute("SELECT MAX(maxOcc) FROM lab7_rooms")
    max_capacity = cursor.fetchone()[0]
    if total_persons > max_capacity:
       print("No suitable rooms available. Requested person count exceeds maximum capacity of any room.")
       return
    
    # SQL query to retrieve available rooms
    query = """
    SELECT r.RoomCode, r.RoomName, r.Beds, r.bedType, r.maxOcc, r.basePrice, r.decor
    FROM lab7_rooms r
    WHERE (r.RoomCode = %s OR %s = 'Any')
    AND (r.bedType = %s OR %s = 'Any')
    AND (r.maxOcc >= %s + %s)
    AND r.RoomCode NOT IN (
       SELECT res.Room
       FROM lab7_reservations res
       WHERE  (res.CheckIn BETWEEN %s AND %s) OR 
           (res.CheckOut BETWEEN %s AND %s)
    )"""
    
    cursor.execute(query, (room_code, room_code, bed_type, bed_type, 
                           num_children, num_adults,
                           begin_date, end_date,
                           begin_date, end_date))

    rows = cursor.fetchall()

    if len(rows) == 0:
        # No exact matches found, suggest 5 possibilities
        print("No exact matches found. Suggesting 5 possibilities:")
        suggested_rooms = get_suggested_rooms(conn, room_code, bed_type, total_persons, begin_date, end_date)
        
        if len(suggested_rooms) == 0:
            print("No rooms match your search. Please try again.")
            return
        else:
            print("No exact matches found. Suggesting 5 possibilities:")
            for i, room in enumerate(suggested_rooms, start=1):
                print(f"{i}. {room[1]} ({room[2]} {room[3]}, {room[4]} max occupancy, ${room[5]} per night)")
        
        while True:
            try:
                choice = int(input("Select a room number to book (or 0 to cancel): "))
                if choice == 0:
                    print("Reservation cancelled.")
                    return
                elif choice < 1 or choice > len(suggested_rooms):
                    raise ValueError
                else:
                    selected_room = suggested_rooms[choice - 1]
                    break
            except ValueError:
                print("Invalid choice. Please enter a valid room number.")


    else: 
        # Display a numbered list of available rooms
        print("Available rooms:")
        for i, row in enumerate(rows):
            print(f"{i+1}. {row[1]} ({row[2]} {row[3]}, {row[4]} max occupancy, ${row[5]} per night)")

        # Prompt user to select a room
        while True:
            try:
                choice = int(input("Select a room number to book (or 0 to cancel): "))
                if choice == 0:
                    print("Reservation cancelled.")
                    return
                elif choice < 1 or choice > len(rows):
                    raise ValueError
                else:
                    selected_room = rows[choice - 1]
                    break
            except ValueError:
                print("Invalid choice. Please enter a valid room number.")

    # calculate total cost and get unique reservation code
    total_cost = calculate_total_cost(selected_room[4], begin_date, end_date)
    code = random.randint(10000, 99999)
    while True:
        cursor.execute("SELECT * FROM lab7_reservations WHERE CODE = %s", (code,))
        if cursor.fetchone() is None:
            break
        else:
            code = random.randint(10000, 99999)

    confirm = input(f"Confirm booking room {selected_room[1]} for ${total_cost} (y/n): ")
    if confirm.lower() != 'y':
        print("Reservation cancelled.")
        return

    cursor.execute("""
        INSERT INTO lab7_reservations (CODE, Room, CheckIn, Checkout, Rate, LastName, FirstName, Adults, Kids)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (code, selected_room[0], begin_date, end_date, selected_room[4], last_name, first_name, num_adults, num_children))
    conn.commit()

    print("\nConfirmation:")
    print(f"First name: {first_name}")
    print(f"Last name: {last_name}")
    print(f"Room code: {selected_room[0]}")
    print(f"Room name: {selected_room[1]}")
    print(f"Bed type: {selected_room[3]}")
    print(f"Begin date of stay: {begin_date}")
    print(f"End date of stay: {end_date}")
    print(f"Number of adults: {num_adults}")
    print(f"Number of children: {num_children}")
    print(f"Total cost of stay: ${total_cost}")

    cursor.close()
    
def calculate_total_cost(base_price, checkin_date, checkout_date):
    total_cost = 0
    checkin_date = datetime.strptime(checkin_date, "%Y-%m-%d")
    checkout_date = datetime.strptime(checkout_date, "%Y-%m-%d")
    current_date = checkin_date
    while current_date < checkout_date:
        if current_date.weekday() < 5: 
            total_cost += base_price
        else: 
            total_cost += base_price * 1.10
        current_date += timedelta(days=1)
    return round(total_cost, 2)    

def get_suggested_rooms(conn, room_code, bed_type, total_persons, begin_date, end_date):
   cursor = conn.cursor()

   # SQL query to get suggested rooms based on similarity
   query = """
   SELECT r.RoomCode, r.RoomName, r.Beds, r.bedType, r.maxOcc, r.basePrice, r.decor
   FROM lab7_rooms r
   WHERE r.maxOcc >= %s
   AND r.RoomCode NOT IN (
       SELECT res.Room
       FROM lab7_reservations res
       WHERE  (res.CheckIn BETWEEN %s AND %s) OR 
           (res.CheckOut BETWEEN %s AND %s)
   )
   LIMIT 5
   """
   cursor.execute(query, (total_persons, begin_date, end_date, begin_date, end_date))
   suggested_rooms = cursor.fetchall()

   cursor.close()
   return suggested_rooms
      
def cancel_res(conn):
    cursor = conn.cursor()
    reservation_code = input("Enter reservation code to cancel: ")

    cursor.execute("SELECT * FROM lab7_reservations WHERE CODE = %s", (reservation_code,))
    reservation = cursor.fetchone()
    if reservation is None:
        print("Reservation not found.")
        return

    print("\nReservation details:")
    print(f"Room: {reservation[1]}")
    print(f"Check-in date: {reservation[2]}")
    print(f"Checkout date: {reservation[3]}")
    print(f"Rate: {reservation[4]}")
    print(f"Last name: {reservation[5]}")
    print(f"First name: {reservation[6]}")
    print(f"Adults: {reservation[7]}")
    print(f"Kids: {reservation[8]}")
    confirm = input("Confirm cancellation (y/n): ")

    if confirm.lower() == 'y':
        # Remove reservation record from the database
        cursor.execute("DELETE FROM lab7_reservations WHERE CODE = %s", (reservation_code,))
        conn.commit()
        print("Reservation successfully cancelled.")
    else:
        print("Cancellation aborted.")

    cursor.close()

def detailed_res_info(conn):
    cursor = conn.cursor()

    print("Search for reservations (leave blank for Any)")
    first_name = input("First name: ") 
    last_name = input("Last name: ") 
    room_code = input("Room code: ") 
    res_code = input("Reservation code: ") 
    begin_date = input("Start date of range (YYYY-MM-DD): ") 
    end_date = input("End date of range (YYYY-MM-DD): ")
        
    if not first_name.strip():
        first_name = "%"
    if not last_name.strip():
        last_name = "%"
    if not room_code.strip():
        room_code = "%"
    if not res_code.strip():
        res_code = "%"
    if not begin_date.strip():
       begin_date = None
    if not end_date.strip():
       end_date = None
        
    query = """
    select r.roomname, res.*
    from lab7_reservations res
    join lab7_rooms r on res.room = r.roomcode
    where res.firstname like %s and
        res.lastname like %s and
         ((%s is null) or 
        (res.checkin < %s and res.checkout >= %s) or
        (%s is null) or 
        (res.checkout > %s and res.checkin < %s) or
        (res.checkin >= %s and res.checkout <= %s)) and
        res.room like %s and
        res.code like %s;
    """
    
    cursor.execute(query, [first_name, last_name, 
                    begin_date, end_date, begin_date,
                    end_date, begin_date, end_date, 
                    begin_date, end_date, 
                    room_code, res_code])

    rows = cursor.fetchall()

    df = pd.DataFrame(rows, columns=[col[0] for col in cursor.description])

    if df.empty:
        print("No reservations matching that query")
    else:
        print(df)
    
    cursor.close()

def revenue(conn):
    cursor = conn.cursor()
    month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    result = []
    for i in range(len(month_names)):
        cursor.execute("""
            with month as (
                select roomname,
                    sum(
                        case
                            when month(res.checkin) = month(res.checkout) then datediff(res.checkout, res.checkin) * baseprice
                            when month(res.checkout) > %s then
                                datediff(
                                    least(last_day(date_format(curdate(), '%%Y-%02d-01')), res.checkout),
                                    greatest(date_format(curdate(), '%%Y-%02d-01'), res.checkin)
                                    ) * baseprice + baseprice
                            when month(res.checkout) = %s then datediff(
                                    res.checkout,
                                    greatest(date_format(curdate(), '%%Y-%02d-01'), res.checkin)
                                    ) * baseprice
                            else 0
                        end
                    ) as total
                from lab7_rooms
                left outer join (select * from lab7_reservations where month(checkin) <= %s and month(checkout) >= %s and year(checkout) = year(curdate())) res on room = roomcode
                group by roomcode
            )
            select 
                month.roomname, 
                month.total as %s
            from month
            order by roomname
        """ % (i + 1, i + 1, i + 1, i + 1, i + 1, i + 1, i + 1, month_names[i]))

        # Fetch all rows from the result
        fetched = cursor.fetchall()
        rows = [row[1] for row in fetched]

        # get roomnames
        rooms = [row[0] for row in fetched]

        # append month result to results list
        result.append(rows)

    # Convert to DataFrame
    df = pd.DataFrame(result).transpose()

    # Transpose the DataFrame
    df.columns = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

    # Add the roomnames
    df.insert(0, "Room Names", rooms)

    # Add the totals
    totals = [sum(month) for month in result]
    totals.insert(0, "totals")
    df.loc[len(df)] = totals

    df["Yearly Total"] = df.iloc[:, 1:].sum(axis=1)

    print(df)

    cursor.close()

if __name__ == "__main__":
    main()

