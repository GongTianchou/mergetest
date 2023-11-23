CREATE TABLE USERS (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    user_type ENUM('ADMIN', 'NORMAL_USER') NOT NULL,
    user_name VARCHAR(30) NOT NULL,
    email VARCHAR(255) UNIQUE,
    balance DECIMAL(10, 2) DEFAULT 0.00,
    seller_rating DECIMAL(3, 2) DEFAULT 0.00,
    buyer_rating DECIMAL(3, 2) DEFAULT 0.00,
    num_of_seller_rating INT DEFAULT 0,
    num_of_buyer_rating INT DEFAULT 0,
    is_allowed_chat BOOLEAN DEFAULT TRUE, -- TRUE means allowd to chat
    is_allow_list BOOLEAN DEFAULT TRUE -- TRUE means allowed to list
);


CREATE TABLE LISTED_VEHICLES (
    listing_id INT PRIMARY KEY,
    vehicle_id INT NOT NULL,
    VIN VARCHAR(17) UNIQUE,
    seller_id INT NOT NULL,
    image_url VARCHAR(255),
    vehicle_description VARCHAR(255),
    make VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    fuel_type VARCHAR(50),
    year_of_production INT,
    mileage INT,
    price INT,
    exterior_color VARCHAR(30),
    interior_color VARCHAR(30),
    state VARCHAR(2),
    zip_code VARCHAR(10),
    is_verified BOOLEAN DEFAULT NULL, -- NULL means verification has not been started
    listing_start_date DATETIME,
    listing_end_date DATETIME,
    listing_status BOOLEAN DEFAULT FALSE, -- FALSE means not active
    FOREIGN KEY (seller_id) REFERENCES USERS(user_id)
);


CREATE TABLE BIDDINGS (
    bidding_id INT PRIMARY KEY,
    listing_id INT NOT NULL,
    user_id INT NOT NULL,
    bidding_amount DECIMAL(10, 2) NOT NULL,
    bidding_date DATETIME NOT NULL,
    is_winner BOOLEAN DEFAULT NULL,
    FOREIGN KEY (listing_id) REFERENCES LISTED_VEHICLES(listing_id),
    FOREIGN KEY (user_id) REFERENCES USERS(user_id)
);


CREATE TABLE RATINGS (
    rating_id INT PRIMARY KEY,
    listing_id INT NOT NULL,
    seller_id INT NOT NULL,
    winner_id INT NOT NULL,
    seller_rate_from_winner DECIMAL(3, 1) NOT NULL,
    winner_rate_from_seller DECIMAL(3, 1) NOT NULL,
    FOREIGN KEY (listing_id) REFERENCES LISTED_VEHICLES(listing_id),
    FOREIGN KEY (seller_id) REFERENCES USERS(user_id),
    FOREIGN KEY (winner_id) REFERENCES USERS(user_id)
);

CREATE TABLE VEHICLE_ORDERS (
    order_id INT PRIMARY KEY,
    listing_id INT NOT NULL,
    buyer_id INT NOT NULL,
    seller_id INT NOT NULL,
    order_price INT NOT NULL,
    order_date DATETIME NOT NULL,
    tracking_number INT,
    is_paid BIT DEFAULT 0 NOT NULL,
    is_shipped BIT DEFAULT 0 NOT NULL,
    FOREIGN KEY (listing_id) REFERENCES LISTED_VEHICLES(listing_id),
    FOREIGN KEY (buyer_id) REFERENCES BIDDINGS(user_id),
    FOREIGN KEY (seller_id) REFERENCES LISTED_VEHICLES(seller_id)
);

CREATE TABLE CHATS (
    chat_id INT PRIMARY KEY NOT NULL,
    sender_id INT NOT NULL,
    receiver_id INT NOT NULL,
    message VARCHAR(200) NOT NULL,
    date DATETIME NOT NULL,
    listing_id INT NOT NULL,
    FOREIGN KEY (sender_id) REFERENCES USERS(user_id),
    FOREIGN KEY (receiver_id) REFERENCES USERS(user_id),
    FOREIGN KEY (listing_id) REFERENCES LISTED_VEHICLES(listing_id)
);

CREATE TABLE BALANCE_TRANSACTIONS (
    transaction_id INT PRIMARY KEY NOT NULL,
    user_id INT NOT NULL,
    current_balance INT NOT NULL,
    date DATETIME NOT NULL,
    transaction_type ENUM('withdraw', 'pop_up', 'pay', 'receive') NOT NULL,
    transaction_amount INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES USERS(user_id)
);

CREATE TABLE VIOLATION_REPORTS (
    report_id INT PRIMARY KEY NOT NULL,
    user_id INT NOT NULL,
    report_content VARCHAR(3000) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES USERS(user_id)
);

# VIEW: Show top 10 rating for normal user
CREATE VIEW Top10RatedSeller AS
SELECT
    user_id,
    user_name,
    seller_rating
FROM USERS
WHERE user_type = 'NORMAL_USER'
ORDER BY seller_rating DESC
LIMIT 10;

# PROCEDURE: Retrieve the bid_id and user_id for highest bidding_amount Bid
DELIMITER //

CREATE PROCEDURE GetHighestBidDetails(_listing_id INT)
BEGIN
    SELECT bidding_id as winner_bidding_id, user_id AS winner_id 
    FROM BIDDINGS 
    WHERE listing_id = _listing_id 
    ORDER BY bidding_amount DESC LIMIT 1;
END //

DELIMITER ;

DELIMITER //

CREATE TRIGGER update_user_ratings
AFTER INSERT ON RATINGS
FOR EACH ROW
BEGIN
    -- Update seller's ratings and count
    UPDATE USERS
    SET
        seller_rating = (
            SELECT AVG(seller_rate_from_winner)
            FROM RATINGS
            WHERE seller_id = NEW.seller_id
        ),
        num_of_seller_rating = (
            SELECT COUNT(*)
            FROM RATINGS
            WHERE seller_id = NEW.seller_id
        )
    WHERE user_id = NEW.seller_id;

    -- Update winner's ratings and count
    UPDATE USERS
    SET
        buyer_rating = (
            SELECT AVG(winner_rate_from_seller)
            FROM RATINGS
            WHERE winner_id = NEW.winner_id
        ),
        num_of_buyer_rating = (
            SELECT COUNT(*)
            FROM RATINGS
            WHERE winner_id = NEW.winner_id
        )
    WHERE user_id = NEW.winner_id;
END;
//


-- Procedure and Event: Update vehicle_listing if listing_end_date is reached. 
-- Also, update BIDDINGS, ORDERS, TRANSACTIONS, USERS table.
CREATE PROCEDURE GetHighestBid(_listing_id INT)
BEGIN
    -- Temporary table to store the highest bid details
    CREATE TEMPORARY TABLE IF NOT EXISTS TempHighestBid (
        bidding_id INT,
        user_id INT,
        bidding_amount DECIMAL(10, 2)
    );

    -- Clearing the temporary table
    TRUNCATE TABLE TempHighestBid;

    -- Inserting the highest bid details into the temporary table
    INSERT INTO TempHighestBid (bidding_id, user_id, bidding_amount)
    SELECT bidding_id, user_id, bidding_amount
    FROM BIDDINGS
    WHERE listing_id = _listing_id 
    ORDER BY bidding_amount DESC LIMIT 1;
END //


CREATE PROCEDURE UpdateExpiredListings()
BEGIN
    DECLARE finished INTEGER DEFAULT 0;
    DECLARE lst_id INT;
    DECLARE high_bid_id INT;
    DECLARE high_bid_user_id INT;
    DECLARE high_bid_amount DECIMAL(10, 2);
    DECLARE seller_id INT;
    DECLARE new_order_id INT;
    DECLARE new_transaction_id INT;

    -- Cursor to select expired listings
    DECLARE expired_listings CURSOR FOR 
        SELECT listing_id 
        FROM LISTED_VEHICLES 
        WHERE listing_end_date < NOW() AND listing_status = TRUE;

    -- Handler for the end of the cursor loop
    DECLARE CONTINUE HANDLER 
        FOR NOT FOUND SET finished = 1;

    OPEN expired_listings;

    listings_loop: LOOP
        FETCH expired_listings INTO lst_id;
        IF finished = 1 THEN 
            LEAVE listings_loop;
        END IF;

        -- Start transaction
        START TRANSACTION;

        -- Updating the listing status
        UPDATE LISTED_VEHICLES
        SET listing_status = FALSE
        WHERE listing_id = lst_id;

        -- Finding the highest bid
        CALL GetHighestBid(lst_id);

        -- Fetch the highest bid details
        SELECT bidding_id, user_id, bidding_amount INTO high_bid_id, high_bid_user_id, high_bid_amount
		FROM TempHighestBid;

        -- Fetch seller ID from listed vehicles
        SELECT seller_id INTO seller_id
        FROM LISTED_VEHICLES
        WHERE listing_id = lst_id;

        -- Create new order
        INSERT INTO VEHICLE_ORDERS (listing_id, buyer_id, seller_id, order_price, order_date)
        VALUES (lst_id, high_bid_user_id, seller_id, high_bid_amount, NOW());

        -- Get the new order ID
        SET new_order_id = LAST_INSERT_ID();

		-- Update balance transactions for buyer
		INSERT INTO BALANCE_TRANSACTIONS (user_id, current_balance, date, transaction_type, transaction_amount)
		SELECT 
			high_bid_user_id, 
			(u.balance - high_bid_amount), 
			NOW(), 
			'pay', 
			high_bid_amount
		FROM USERS u
		WHERE u.user_id = high_bid_user_id;

		-- Update balance transactions for seller
		INSERT INTO BALANCE_TRANSACTIONS (user_id, current_balance, date, transaction_type, transaction_amount)
		SELECT 
			seller_id, 
			(u.balance + high_bid_amount), 
			NOW(), 
			'receive', 
			high_bid_amount
		FROM USERS u
		WHERE u.user_id = seller_id;
        
    END LOOP;

    CLOSE expired_listings;

END //
DELIMITER ;
    
CREATE EVENT update_listing_status
ON SCHEDULE EVERY 1 day
STARTS CURRENT_TIMESTAMP
DO
    CALL UpdateExpiredListings();





