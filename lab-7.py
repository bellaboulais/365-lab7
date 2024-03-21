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
            #elif option == "2":
             #   reservations(conn)
            elif option == "3":
                cancel_res(conn)
            #elif option == "4":
             #   detailed_reservation_info(conn)
            #elif option == "5":
             #   revenue(conn)
            elif option == "6":
                break
            else:
                print("Invalid option. Please try again.")
    finally: 
        conn.close()


def room_rates(conn):
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.RoomCode, r.RoomName,
            ROUND((SELECT COUNT(*) FROM lab7_reservations WHERE Room = r.RoomCode AND CheckIn BETWEEN DATE_SUB(CURDATE(), INTERVAL 180 DAY) AND CURDATE()) / 180, 2) AS PopularityScore,
            (SELECT MIN(CheckIn) FROM lab7_reservations WHERE Room = r.RoomCode AND CheckIn > CURDATE()) AS NextCheckIn,
            (SELECT DATEDIFF(Checkout, CheckIn) FROM lab7_reservations WHERE Room = r.RoomCode AND CheckOut < CURDATE() ORDER BY CheckOut DESC LIMIT 1) AS LengthOfMostRecentStay
        FROM
            lab7_rooms r
        ORDER BY
            PopularityScore DESC;
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

#def deatiled_res_info(conn):

#def revenue(conn):


if __name__ == "__main__":
    main()
    # 365-w24-027257145