-- =====================================================================
-- Berlin Airbnb: business questions answered in SQL (SQLite dialect)
-- Table: listings  (created from data/processed/listings_clean.csv)
-- =====================================================================

-- Q1. Which districts are the most expensive, and how big is each market?
SELECT district,
       COUNT(*)                         AS listings,
       ROUND(AVG(price), 0)             AS avg_price,
       ROUND(AVG(price_per_guest), 0)   AS avg_price_per_guest,
       ROUND(100.0 * SUM(room_type = 'Entire home/apt') / COUNT(*), 1) AS pct_entire_home
FROM listings
GROUP BY district
ORDER BY avg_price DESC;

-- Q2. How do prices differ by room type?
SELECT room_type,
       COUNT(*)                                        AS listings,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM listings), 1) AS pct_of_market,
       ROUND(AVG(price), 0)                            AS avg_price
FROM listings
GROUP BY room_type
ORDER BY listings DESC;

-- Q3. How concentrated is the market? Share of listings run by multi-listing hosts
SELECT host_type,
       COUNT(*)                                        AS listings,
       COUNT(DISTINCT host_id)                         AS hosts,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM listings), 1) AS pct_of_listings
FROM listings
GROUP BY host_type;

-- Q4. Top 10 hosts by number of active listings
SELECT host_id,
       COUNT(*)                 AS listings,
       ROUND(AVG(price), 0)     AS avg_price,
       GROUP_CONCAT(DISTINCT district) AS districts
FROM listings
GROUP BY host_id
ORDER BY listings DESC
LIMIT 10;

-- Q5. Regulation: how many short-term listings (< 30 nights) show a registration
--     number or business disclosure, by district?
SELECT district,
       COUNT(*) AS short_term_listings,
       ROUND(100.0 * SUM(license_status = 'Registration number')        / COUNT(*), 1) AS pct_registration_no,
       ROUND(100.0 * SUM(license_status = 'Business / host disclosure') / COUNT(*), 1) AS pct_business_disclosure,
       ROUND(100.0 * SUM(license_status = 'Missing')                    / COUNT(*), 1) AS pct_missing
FROM listings
WHERE short_term = 1
GROUP BY district
ORDER BY pct_missing DESC;

-- Q6. Do superhosts charge more and get better reviews?
SELECT CASE WHEN superhost = 1 THEN 'Superhost' ELSE 'Regular host' END AS host_status,
       COUNT(*)                       AS listings,
       ROUND(AVG(price), 0)           AS avg_price,
       ROUND(AVG(review_score), 2)    AS avg_rating,
       ROUND(AVG(est_occupancy_nights), 0) AS avg_booked_nights
FROM listings
GROUP BY superhost;

-- Q7. Estimated annual revenue by district (entire homes only)
SELECT district,
       COUNT(*)                          AS entire_homes,
       ROUND(AVG(est_occupancy_nights))  AS avg_booked_nights,
       ROUND(AVG(est_revenue), -2)       AS avg_est_revenue
FROM listings
WHERE room_type = 'Entire home/apt'
GROUP BY district
HAVING COUNT(*) >= 50
ORDER BY avg_est_revenue DESC;
