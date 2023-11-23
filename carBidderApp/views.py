from django.shortcuts import render, redirect
from django.db import connection
from django.contrib.auth.hashers import make_password
from django.http import HttpResponseRedirect
from datetime import datetime, timedelta
from django.http import Http404, HttpResponseRedirect, HttpResponseForbidden, HttpResponseNotFound
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse
from django.db import IntegrityError
from datetime import datetime
import uuid
from django.contrib import messages
import openai
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Access the API key
api_key = os.getenv('MY_API_KEY')

cur_user = {}


def home(request):

    user_type = request.session.get('user_type', '')
    user_name = request.session.get('user_name', '')
    context = {
        'user_type': user_type,
        'user_name': user_name,
    }
    return render(request, 'home.html', context)


def is_email_valid(email):
    with connection.cursor() as cursor:
        cursor.execute("SELECT email FROM USERS WHERE email = %s", [email])
        return cursor.fetchone() is not None


def register(request):
    message = None

    if request.method == "POST":
        user_type = request.POST.get('user_type', '')
        user_name = request.POST.get('user_name', '')
        email = request.POST.get('email', '')

        if not is_email_valid(email):  # Check if the email is not already in use
            try:
                with connection.cursor() as cursor:
                    query = """
                        INSERT INTO USERS (user_type, user_name, email)
                        VALUES (%s, %s, %s);
                    """
                    cursor.execute(query, (user_type, user_name, email))
                    connection.commit()

                message = "Registration successful! "
            except Exception as e:
                print(f"An error occurred: {e}")
                message = "An error occurred during registration. Please try again."
        else:
            message = "Email already in use. Please choose a different email."

    return render(request, 'register.html', {'message': message, 'current_page': 'register'})


def update_session(request, email):
    """
    Update the session with the user's data based on the provided email.
    """
    try:
        with connection.cursor() as cursor:
            query = """
                SELECT * 
                FROM USERS
                WHERE email = %s;
            """
            cursor.execute(query, [email])
            user_data = cursor.fetchone()

            if user_data:
                # Extracting user data and updating the session
                request.session['user_id'] = user_data[0]
                request.session['user_type'] = user_data[1]
                request.session['user_name'] = user_data[2]
                request.session['email'] = user_data[3]
                request.session['balance'] = str(
                    user_data[4])  # Convert Decimal to string
                request.session['seller_rating'] = str(
                    user_data[5])  # Convert Decimal to string
                request.session['buyer_rating'] = str(
                    user_data[6])  # Convert Decimal to string
                request.session['num_of_seller_rating'] = user_data[7]
                request.session['num_of_buyer_rating'] = user_data[8]
                request.session['is_allow_chat'] = user_data[9]
                request.session['is_allow_list'] = user_data[10]
            else:
                # Handle case where user data is not found
                # You can redirect to an error page or set an error message
                pass

    except Exception as e:
        print(f"An error occurred: {e}")
        # Optionally, handle the exception (e.g., set an error message, redirect)


def login(request):
    error_message = None  # Variable to hold the error message

    if request.method == "POST":
        user_email = request.POST.get('email', '')

        if user_email:
            try:
                if is_email_valid(user_email):
                    update_session(request, user_email)
                    return redirect('home')
                else:
                    error_message = "Email does not exist. Please try again or"
            except Exception as e:
                print(f"An error occurred: {e}")
                error_message = "An error occurred during login. Please try again."
        else:
            error_message = "Please enter an email address."

    return render(request, 'login.html', {'error_message': error_message, 'current_page': 'login'})


def is_email_valid(email):
    with connection.cursor() as cursor:
        cursor.execute("SELECT email FROM USERS WHERE email = %s", [email])
        return cursor.fetchone() is not None


def logout(request):
    request.session.flush()
    return redirect('home')


def profile(request):
    user_email = request.session.get('email', '')
    if user_email:
        update_session(request, user_email)

    # Fetching data from the session
    user_id = request.session.get('user_id', '')
    user_type = request.session.get('user_type', '')
    user_name = request.session.get('user_name', '')
    email = request.session.get('email', '')
    balance = request.session.get('balance', '')
    seller_rating = request.session.get('seller_rating', '')
    buyer_rating = request.session.get('buyer_rating', '')
    num_of_seller_rating = request.session.get('num_of_seller_rating', '')
    num_of_buyer_rating = request.session.get('num_of_buyer_rating', '')
    is_allow_chat = request.session.get('is_allow_chat', '')
    is_allow_list = request.session.get('is_allow_list', '')

    # Fetch the listings vehicles from the database
    listings = []
    if user_id:
        try:
            with connection.cursor() as cursor:
                query = """
                    SELECT listing_id, make, model, year_of_production, image_url, listing_status, listing_start_date
                    FROM LISTED_VEHICLES
                    WHERE seller_id = %s;
                """
                cursor.execute(query, [user_id])
                listings = cursor.fetchall()
        except Exception as e:
            print(f"An error occurred: {e}")
            # Handle the error

    # Fetch the user's biddings from the database
    biddings = []

    if user_id:
        try:
            with connection.cursor() as cursor:
                query = """
                    SELECT b.bidding_id, b.listing_id, v.make, v.model, v.year_of_production, 
                        v.image_url, v.listing_status, b.bidding_amount, b.bidding_date, b.is_winner,
                        s.user_id, s.user_name
                    FROM BIDDINGS b
                    INNER JOIN LISTED_VEHICLES v ON b.listing_id = v.listing_id
                    INNER JOIN USERS s ON v.seller_id = s.user_id
                    WHERE b.user_id = %s;
                """
                cursor.execute(query, [user_id])
                biddings = cursor.fetchall()
        except Exception as e:
            print(f"An error occurred: {e}")
            # Handle the error

    # Creating the context dictionary
    context = {
        'user_id': user_id,
        'user_type': user_type,
        'user_name': user_name,
        'email': email,
        'balance': balance,
        'seller_rating': seller_rating,
        'buyer_rating': buyer_rating,
        'num_of_seller_rating': num_of_seller_rating,
        'num_of_buyer_rating': num_of_buyer_rating,
        'is_allow_chat': is_allow_chat,
        'is_allow_list': is_allow_list,
        'listings': listings,
        'biddings': biddings,
        'current_page': 'profile',
    }

    return render(request, 'profile.html', context)


def report(request):
    user_email = request.session.get('email', '')
    if user_email:
        update_session(request, user_email)

    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM VIOLATION_REPORTS")
        violation_reports = cursor.fetchall()

    if request.method == 'POST':
        report_id_to_delete = request.POST.get('report_id_to_delete')
        if report_id_to_delete:
            # Delete the report with the specified report_id using a cursor
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM VIOLATION_REPORTS WHERE report_id = %s", [
                               report_id_to_delete])

            # Redirect back to the report page after deleting
            return redirect('report')

    # Add violation reports to the context
    user_type = request.session.get('user_type', '')
    user_name = request.session.get('user_name', '')
    context = {
        'violation_reports': violation_reports,
        'user_type': user_type,
        'user_name': user_name,
        'current_page': 'violation_reports',
    }

    return render(request, 'report.html', context)


def users(request):
    user_email = request.session.get('email', '')
    if user_email:
        update_session(request, user_email)

    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM USERS")
        users = cursor.fetchall()

    if request.method == 'POST':
        user_id_to_toggle_mute = request.POST.get('user_id_to_toggle_mute')
        if user_id_to_toggle_mute:
            with connection.cursor() as cursor:
                # Check if the user is currently muted or not
                cursor.execute("SELECT is_allowed_chat FROM USERS WHERE user_id = %s", [
                               user_id_to_toggle_mute])
                is_muted = cursor.fetchone()[0]

                # Toggle mute status
                new_status = not is_muted
                cursor.execute("UPDATE USERS SET is_allowed_chat = %s WHERE user_id = %s", [
                               new_status, user_id_to_toggle_mute])

            return redirect('users')

    if request.method == 'POST':
        user_id_to_toggle_list = request.POST.get('user_id_to_toggle_list')
        if user_id_to_toggle_list:
            with connection.cursor() as cursor:
                # Check the current listing permission of the user
                cursor.execute("SELECT is_allow_list FROM USERS WHERE user_id = %s", [
                               user_id_to_toggle_list])
                can_list = cursor.fetchone()[0]

                # Toggle the permission
                new_list_status = not can_list
                cursor.execute("UPDATE USERS SET is_allow_list = %s WHERE user_id = %s", [
                               new_list_status, user_id_to_toggle_list])

            return redirect('users')

    # Add violation reports to the context
    user_type = request.session.get('user_type', '')
    user_name = request.session.get('user_name', '')
    context = {
        'users': users,
        'user_type': user_type,
        'user_name': user_name,
        'current_page': 'users',
    }

    return render(request, 'users.html', context)


def verify_vehicles(request):
    user_email = request.session.get('email', '')
    if user_email:
        update_session(request, user_email)

    # Check if the request is a POST to update verification status
    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle_id')
        verification_action = request.POST.get('verification_action')

        new_status = None
        if verification_action == 'Verify':
            new_status = True
        elif verification_action == 'NotVerify':
            new_status = False
        # 'Not Started' will be represented by None, so no need for an explicit check

        # Update the database
        with connection.cursor() as cursor:
            cursor.execute("UPDATE LISTED_VEHICLES SET is_verified = %s WHERE vehicle_id = %s", [
                           new_status, vehicle_id])

        # Redirect to the same page to prevent form resubmission on page refresh
        return redirect('verify_vehicles')

    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM LISTED_VEHICLES")
        vehicles = cursor.fetchall()

    user_type = request.session.get('user_type', '')
    user_name = request.session.get('user_name', '')

    context = {
        'vehicles': vehicles,
        'user_type': user_type,
        'user_name': user_name,
        'current_page': 'verify_vehicles',
    }

    return render(request, 'verify_vehicles.html', context)


def add_funds(request):
    if request.method == "POST":
        user_id = request.session.get('user_id')
        amount = request.POST.get('amount')

        # Only proceed if the user is logged in as a normal user
        if not user_id or request.session.get('user_type') != 'NORMAL_USER':
            # Redirect to home or show an error
            return HttpResponseRedirect('/')

        try:
            # Update the user's balance in the database
            with connection.cursor() as cursor:
                query = """
                    UPDATE USERS
                    SET balance = balance + %s
                    WHERE user_id = %s;
                """
                cursor.execute(query, (amount, user_id))
                connection.commit()
        except Exception as e:
            print(f"An error occurred: {e}")
            # Handle the error (e.g., set an error message)

        # Optionally, update the session balance
        request.session['balance'] = str(
            float(request.session.get('balance', 0)) + float(amount))

        # Redirect to the profile page or show a success message
        return HttpResponseRedirect('/profile/')
    else:
        # Redirect or show an error if accessed directly
        return HttpResponseRedirect('/')


def orders(request):
    user_email = request.session.get('email', '')
    if user_email:
        update_session(request, user_email)

    user_id = request.session.get('user_id', '')
    user_type = request.session.get('user_type', '')
    user_name = request.session.get('user_name', '')

    # Fetch orders from the database
    orders = []
    if user_id:
        try:
            with connection.cursor() as cursor:
                query = """
                    SELECT vo.order_id, vo.listing_id, lv.image_url, vo.order_price, 
                           vo.order_date, vo.is_shipped, vo.tracking_number, vo.is_paid
                    FROM VEHICLE_ORDERS vo
                    INNER JOIN LISTED_VEHICLES lv ON vo.listing_id = lv.listing_id
                    WHERE vo.buyer_id = %s;
                """
                cursor.execute(query, [user_id])
                orders = cursor.fetchall()
        except Exception as e:
            print(f"An error occurred: {e}")
            # Handle the error

    context = {'orders': orders,
               'user_type': user_type,
               'user_name': user_name,
               'current_page': 'orders',
               }
    return render(request, 'orders.html', context)


def weekly_reports(request):
    user_email = request.session.get('email', '')
    if user_email:
        update_session(request, user_email)

    user_type = request.session.get('user_type', '')
    user_name = request.session.get('user_name', '')

    start_date = None
    end_date = None
    vehicle_start_date = None
    vehicle_end_date = None
    if 'start_date' in request.POST:
        # Default start_date and end_date as None
        request.session['start_date'] = request.POST.get('start_date')
        request.session['end_date'] = request.POST.get('end_date')

    elif 'vehicle_start_date' in request.POST:
        request.session['vehicle_start_date'] = request.POST.get(
            'vehicle_start_date')
        request.session['vehicle_end_date'] = request.POST.get(
            'vehicle_end_date')

    # Retrieve from session if available
    start_date = request.session.get('start_date', '')
    end_date = request.session.get('end_date', '')
    vehicle_start_date = request.session.get('vehicle_start_date', '')
    vehicle_end_date = request.session.get('vehicle_end_date', '')

    # get sales report
    report_data = None
    if start_date and end_date:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT SUM(order_price) AS TotalSaleAmount, COUNT(order_id) AS TotalNumberOfSales 
                FROM VEHICLE_ORDERS 
                WHERE order_date BETWEEN %s AND %s
            """, [start_date, end_date])

            report_data = cursor.fetchone()

    popular_vehicles = None
    if vehicle_start_date and vehicle_end_date:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    listing_id, 
                    make, 
                    model, 
                    year_of_production, 
                    number_of_bids
                FROM (
                    SELECT 
                        LV.listing_id AS listing_id, 
                        LV.make AS make, 
                        LV.model AS model, 
                        LV.year_of_production AS year_of_production, 
                        COUNT(*) AS number_of_bids,
                        DENSE_RANK() OVER (ORDER BY COUNT(*) DESC) AS bid_rank
                    FROM 
                        LISTED_VEHICLES AS LV
                    JOIN 
                        BIDDINGS AS B ON LV.listing_id = B.listing_id
                    WHERE 
                        B.bidding_date BETWEEN %s AND %s
                    GROUP BY 
                        LV.listing_id
                ) AS ranked_listings
                WHERE 
                    bid_rank <= 5;
            """, [vehicle_start_date, vehicle_end_date])
            popular_vehicles = cursor.fetchall()

    top_sellers = None
    # Fetch top sellers data
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT user_id, user_name, seller_rating, num_of_seller_rating
            FROM USERS
            WHERE user_type = 'NORMAL_USER'
            ORDER BY seller_rating DESC, num_of_seller_rating DESC
            LIMIT 10
        """)
        top_sellers = cursor.fetchall()

    print(start_date)
    print(end_date)
    print(vehicle_start_date)
    print(vehicle_end_date)
    context = {
        'user_type': user_type,
        'user_name': user_name,
        'current_page': 'weekly_reports',
        'report_data': report_data,
        'start_date': start_date,
        'end_date': end_date,
        'top_sellers': top_sellers,
        'popular_vehicles': popular_vehicles,
        'vehicle_start_date': vehicle_start_date,
        'vehicle_end_date': vehicle_end_date,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'weekly_reports.html', context)


def other_user_profile(request, other_user_id):
    user_type = request.session.get('user_type', '')
    user_name = request.session.get('user_name', '')

    try:
        with connection.cursor() as cursor:
            # Fetch user's user_type
            cursor.execute(
                "SELECT user_type FROM USERS WHERE user_id = %s",
                [other_user_id])
            other_user_type = cursor.fetchone()

            # Check if the other user is ADMIN
            if other_user_type and other_user_type[0] == 'ADMIN':
                return HttpResponseForbidden("Admin User, Access Denied")

            # Fetch user details
            cursor.execute(
                "SELECT user_name, seller_rating, buyer_rating FROM USERS WHERE user_id = %s",
                [other_user_id])
            other_user_details = cursor.fetchone()

            # Fetch listed vehicles
            if other_user_details:
                cursor.execute(
                    "SELECT listing_id, make, model, year_of_production, image_url FROM LISTED_VEHICLES WHERE seller_id = %s",
                    [other_user_id])
                listed_vehicles = cursor.fetchall()

    except Exception as e:
        print(f"An error occurred: {e}")
        # Return a 404 response for missing user ID
        return HttpResponseNotFound("404 User not found")

    if other_user_details is None:
        # Return a 404 response for missing user ID
        return HttpResponseNotFound("404 User not found")

    context = {
        "other_user_id": other_user_id,
        'user_details': other_user_details,
        'listed_vehicles': listed_vehicles,
        'user_type': user_type,
        'user_name': user_name,
    }
    return render(request, 'other_user_profile.html', context)


def search_car(request):
    user_email = request.session.get('email', '')
    if user_email:
        update_session(request, user_email)

    # Fetching data from the session
    user_id = request.session.get('user_id', '')

    # Fetch unique values for dropdowns from the database
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT DISTINCT make FROM LISTED_VEHICLES ORDER BY make")
        makes = [row[0] for row in cursor.fetchall()]

        cursor.execute(
            "SELECT DISTINCT year_of_production FROM LISTED_VEHICLES ORDER BY year_of_production")
        years = [row[0] for row in cursor.fetchall()]

        cursor.execute(
            "SELECT DISTINCT mileage FROM LISTED_VEHICLES ORDER BY mileage")
        mileages = [row[0] for row in cursor.fetchall()]

        cursor.execute(
            "SELECT DISTINCT price FROM LISTED_VEHICLES ORDER BY price")
        prices = [row[0] for row in cursor.fetchall()]

    error_message = None

    # Fetch filter parameters
    make = request.GET.get('make')
    min_year = request.GET.get('min_year')
    max_year = request.GET.get('max_year')
    min_mileage = request.GET.get('min_mile')
    max_mileage = request.GET.get('max_mile')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    # Check for invalid filter ranges
    if min_year and max_year and int(min_year) > int(max_year):
        error_message = "Minimum year cannot be greater than maximum year."
    elif min_mileage and max_mileage and int(min_mileage) > int(max_mileage):
        error_message = "Minimum mileage cannot be greater than maximum mileage."
    elif min_price and max_price and int(min_price) > int(max_price):
        error_message = "Minimum price cannot be greater than maximum price."

    # If there's an error, return early with the error message
    if error_message:
        return render(request, 'search_car.html', {'error_message': error_message})

    # Initialize the base query
    query = "SELECT * FROM LISTED_VEHICLES WHERE listing_status = TRUE"

    # Initialize the parameters list
    params = []

    # Append conditions to the query based on provided filters
    if make:
        query += " AND make = %s"
        params.append(make)

    if min_year:
        query += " AND year_of_production >= %s"
        params.append(min_year)

    if max_year:
        query += " AND year_of_production <= %s"
        params.append(max_year)

    if min_mileage:
        query += " AND mileage >= %s"
        params.append(min_mileage)

    if max_mileage:
        query += " AND mileage <= %s"
        params.append(max_mileage)

    if min_price:
        query += " AND price >= %s"
        params.append(min_price)

    if max_price:
        query += " AND price <= %s"
        params.append(max_price)

    # Fetch the search term
    search_words = []
    search_term = request.GET.get('search_term', '').strip()

    # Check if search term is not empty
    if search_term:
        search_words = search_term.split()

    # Initialize search_words as an empty list
    search_words = []

    # Fetch the search term
    search_term = request.GET.get('search_term', '').strip()

    # Check if search term is not empty
    if search_term:
        search_words = search_term.split()

        # Build the search query only if there are search words
        search_query = " AND ("
        search_query_parts = []
        for word in search_words:
            search_query_parts.append(
                "(make LIKE %s OR model LIKE %s OR exterior_color LIKE %s OR "
                "vehicle_description LIKE %s OR fuel_type LIKE %s OR CAST(year_of_production AS CHAR) LIKE %s)")
            params.extend(["%" + word + "%"] * 6)

        # Only append if there are parts to the search query
        if search_query_parts:
            search_query += " OR ".join(search_query_parts) + ")"
            query += search_query

    vehicles = []
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            vehicles.append(dict(zip(columns, row)))

    user_name = request.session.get('user_name', '')
    user_type = request.session.get('user_type', '')

    return render(request, 'search_car.html', {
        'user_name': user_name,
        'user_type': user_type,
        'vehicles': vehicles,
        'makes': makes,
        'years': years,
        'mileages': mileages,
        'prices': prices,
        'error_message': error_message,
    })


def product_detail(request, listing_id):
    result = None
    current_bid = None

    with connection.cursor() as cursor:
        # SQL query to join USERS and LISTED_VEHICLES tables
        cursor.execute("""
            SELECT LV.*, U.*
            FROM LISTED_VEHICLES AS LV
            JOIN USERS AS U ON LV.seller_id = U.user_id
            WHERE LV.listing_id = %s
        """, [listing_id])

        result = cursor.fetchone()

    # If no product is found, raise a 404 error
    if not result:
        raise Http404("Product does not exist")

    # Check if the current user has bid on this product

    # need modification
    # hardcoded
    current_user_id = 2
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT bidding_amount FROM BIDDINGS
            WHERE listing_id = %s AND user_id = %s
            ORDER BY bidding_date DESC
            LIMIT 1
        """, [listing_id, current_user_id])
        current_bid = cursor.fetchone()

    # Map the result to a dictionary for easy access in the template
    product_dict = {
        'listing_id': result[0],
        'VIN': result[2],
        'image_url': result[4],
        'vehicle_description': result[5],
        'make': result[6],
        'model': result[7],
        'fuel_type': result[8],
        'year_of_production': result[9],
        'mileage': result[10],
        'price': result[11],
        'exterior_color': result[12],
        'interior_color': result[13],
        'state': result[14],
        'zip_code': result[15],
        'seller_name': result[22],
        'seller_rating': result[25],
        'current_bid': current_bid[0] if current_bid else None,
    }

    # return render(request, 'product_detail.html', {'product': product_dict})
    if request.method == 'POST':
        bid_amount = request.POST.get('bid_amount')
        # Assuming user authentication
        user_id = request.user.id

        # Convert bid amount to a decimal or float as needed
        bid_amount = float(bid_amount)

        # Insert the bid into the database
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO BIDDINGS (listing_id, user_id, bidding_amount, bidding_date)
                VALUES (%s, %s, %s, NOW())
            """, [listing_id, user_id, bid_amount])
            # If the bid is successfully placed, add a success message
            messages.success(request, 'Bid placed successfully!')
            # Redirect to the same page to display the success message
            return redirect('bid_success', listing_id=listing_id, user_id=request.user.id)

    user_name = request.session.get('user_name', '')
    user_type = request.session.get('user_type', '')

    # For GET requests or if the bid placement is not successful, render the page with product details
    return render(request, 'product_detail.html', {
        'product': product_dict,
        'user_name': user_name,
        'user_type': user_type,
    })


def bid(request, listing_id):
    if request.method == 'POST':
        try:
            bid_amount = float(request.POST['bid_amount'])

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT price FROM LISTED_VEHICLES WHERE listing_id = %s", [listing_id])
                product_price = cursor.fetchone()
                if not product_price or bid_amount < product_price[0]:
                    # Handle bid amount lower than product price
                    return render(request, 'error.html', {'error_message': 'Bid amount must be higher than the product price'})

                cursor.execute("SELECT MAX(bidding_id) FROM BIDDINGS")
                max_id_result = cursor.fetchone()
                new_bidding_id = max_id_result[0] + \
                    1 if max_id_result[0] else 1

                cursor.execute("""
                    INSERT INTO BIDDINGS (bidding_id, listing_id, user_id, bidding_amount, bidding_date, is_winner)
                    VALUES (%s, %s, 2, %s, %s, %s)
                """, [new_bidding_id, listing_id, bid_amount, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), False])
                connection.commit()

            return redirect('product_detail', listing_id=listing_id)
        except IntegrityError as e:
            print(e)
            # Handle the error, perhaps show a message to the user

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT LV.*, U.*
            FROM LISTED_VEHICLES AS LV
            JOIN USERS AS U ON LV.seller_id = U.user_id 
            WHERE LV.listing_id = %s
        """, [listing_id])

        result = cursor.fetchone()

    user_name = request.session.get('user_name', '')
    user_type = request.session.get('user_type', '')

    product_dict = {
        'user_name': user_name,
        'user_type': user_type,
        'image_url': result[4],
        'make': result[6],
        'model': result[7],
        'price': result[11],
    }

    user_name = request.session.get('user_name', '')
    user_type = request.session.get('user_type', '')

    return render(request, 'bid.html', {
        'product': product_dict,
        'listing_id': listing_id,
        'user_name': user_name,
        'user_type': user_type,
    })


def chatbot(request):
    user_name = request.session.get('user_name', '')
    user_type = request.session.get('user_type', '')

    return render(request, 'chatbot.html', {

        'user_name': user_name,
        'user_type': user_type,
    })


@csrf_exempt
@require_POST
def chat(request):
    data = json.loads(request.body)
    user_message = data.get('message')

    # You need to configure your OpenAI API key
    openai.api_key = api_key

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_message}]
        )
        return JsonResponse({'response': response.choices[0].message['content']})
    except Exception as e:
        return JsonResponse({'response': str(e)}, status=500)


# def bid_success(request, listing_id):
#     # need modification
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT *
#             FROM BIDDINGS
#             WHERE listing_id = %s
#         """, [listing_id])

#         result = cursor.fetchone()

#     # Map the result to a dictionary for easy access in the template
#     bidding_dict = {
#         'bidding_amount': result[3],
#     }

#     return render(request, 'bid.html', {'bidding': bidding_dict})

# # views.py
