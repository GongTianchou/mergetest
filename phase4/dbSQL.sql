/*  1. Get the vehicle information of a listing and bidding amount of the winner.  */ 
SELECT L.vin, U.user_name AS seller, L.vehicle_description, L.make, L.model, B.bidding_amount
FROM LISTED_VEHICLES L
JOIN BIDDINGS B ON B.listing_id = L.listing_id
JOIN USERS U ON U.user_id = L.seller_id
WHERE B.listing_id = 5 AND B.is_winner = TRUE;


/*  2. Get the name list of bidders of a specific listing.  */ 
SELECT DISTINCT(U.user_id), U.user_name, U.email
FROM USERS U
JOIN BIDDINGS B ON B.user_id = U.user_id
WHERE B.listing_id = 5;


/*  3. Display messages between user A and user B about a listed_vehicle.  */ 
SELECT C.chat_id, C.message, C.date, C.listing_id, Sender.user_name AS sender_name, Receiver.user_name AS receiver_name
FROM CHATS C
JOIN USERS Sender ON C.sender_id = Sender.user_id
JOIN USERS Receiver ON C.receiver_id = Receiver.user_id
WHERE ((Sender.user_id = 2 AND Receiver.user_id = 3) OR
      (Sender.user_id = 3 AND Receiver.user_id = 2))
      AND C.listing_id = 1
ORDER BY C.date;


/*  4. Get the total number of bids and average bidding price of users whose
	average bidding amount is greater than 25000.  */ 
SELECT U.user_name, COUNT(B.bidding_id) AS total_bids, AVG(B.bidding_amount) AS average_bid_amount
FROM USERS U 
JOIN BIDDINGS B ON U.user_id = B.user_id
GROUP BY B.user_id
HAVING AVG(B.bidding_amount)>25000
ORDER BY U.user_name;


/*  5. Get top 3 sellers of a month whose total orders is more than 0 */
SELECT U.user_id, U.user_name, COUNT(O.order_id) AS total_orders
FROM VEHICLE_ORDERS O 
JOIN USERS U ON O.seller_id = U.user_id
WHERE O.order_date BETWEEN '2023-01-02' AND '2023-02-02'
GROUP BY O.seller_id
HAVING total_orders>=1
ORDER BY total_orders DESC
LIMIT 3;


/*  6. Find users who have reported violations and the number of reports they made. */
SELECT U.user_id, U.user_name, R.number_of_reports
FROM USERS U
LEFT JOIN
    (
    SELECT user_id, COUNT(report_id) AS number_of_reports
	FROM VIOLATION_REPORTS
	GROUP BY user_id
    ) R 
ON U.user_id = R.user_id
WHERE R.number_of_reports > 0;



