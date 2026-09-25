-- Kiem tra CSDL Sakila tren server MySQL cua ban (chay trong MySQL Workbench / DBeaver / mysql CLI)
-- Ket qua DUNG phai la:
-- total_revenue = 67406.56 | late_fee_revenue = 20262.76 | payments = 16044
-- completed_rentals = 15861 | late_rentals = 8121 | late_rate_pct = 51.20

USE sakila;

SELECT
    ROUND(SUM(p.amount), 2)                                   AS total_revenue,
    ROUND(SUM(GREATEST(p.amount - f.rental_rate, 0)), 2)      AS late_fee_revenue,
    ROUND(SUM(p.amount) - SUM(GREATEST(p.amount - f.rental_rate, 0)), 2) AS rental_revenue,
    COUNT(*)                                                  AS payments
FROM payment p
JOIN rental r    ON p.rental_id = r.rental_id
JOIN inventory i ON r.inventory_id = i.inventory_id
JOIN film f      ON i.film_id = f.film_id;

SELECT
    COUNT(*) AS completed_rentals,
    SUM(r.return_date > DATE_ADD(r.rental_date, INTERVAL f.rental_duration DAY)) AS late_rentals,
    ROUND(SUM(r.return_date > DATE_ADD(r.rental_date, INTERVAL f.rental_duration DAY)) / COUNT(*) * 100, 2) AS late_rate_pct
FROM rental r
JOIN inventory i ON r.inventory_id = i.inventory_id
JOIN film f      ON i.film_id = f.film_id
WHERE r.return_date IS NOT NULL;
