import mysql.connector
import getpass
import pandas as pd
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
    
    while True:
        option = input("\nEnter option number: ")

        if option == "1":
            room_rates(conn)
        elif option == "2":
            reservations(conn)
        elif option == "3":
            cancel_res(conn)
        #elif option == "4":
            #detailed_reservation_info(conn)
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
    begin_date = datetime.strptime(input("Begin date of stay (YYYY-MM-DD): "), "%Y-%m-%d")
    end_date = datetime.strptime(input("End date of stay (YYYY-MM-DD): "), "%Y-%m-%d")
    num_children = int(input("Number of children: "))
    num_adults = int(input("Number of adults: "))
    
    
    cursor.close()
      
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
    # 365-w24-027257145