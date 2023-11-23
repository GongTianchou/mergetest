-- Drop tables if tables are exist
DROP TABLE IF EXISTS VIOLATION_REPORTS;
DROP TABLE IF EXISTS BALANCE_TRANSACTIONS;
DROP TABLE IF EXISTS CHATS;
DROP TABLE IF EXISTS VEHICLE_ORDERS;
DROP TABLE IF EXISTS RATINGS;
DROP TABLE IF EXISTS BIDDINGS;
DROP TABLE IF EXISTS LISTED_VEHICLES;
DROP TABLE IF EXISTS USERS;

# Drop view if tables are exist
DROP VIEW IF EXISTS Top10RatedSeller;

# Drop function if tables are exist
Drop PROCEDURE GetHighestBidDetails;
dROP procedure GetHighestBid;
drop procedure UpdateExpiredListings;


-- Drop triggers if triggers are exist
DROP TRIGGER IF EXISTS update_user_ratings;
