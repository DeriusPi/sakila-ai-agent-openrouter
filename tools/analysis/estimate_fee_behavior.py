# tools/analysis/estimate_fee_behavior.py

from collections import defaultdict
from statistics import mean


def estimate_fee_behavior(
    rental_data=None,
    film_data=None,
    customer_data=None
):
    """
    Estimate a data-derived behavioral response to late-fee changes.

    IMPORTANT:
    Sakila does not contain historical observations of different
    late-fee levels. Therefore this tool does NOT claim to estimate
    causal price elasticity.

    Instead, it derives a behavioral sensitivity proxy from observed
    Sakila rental behavior.

    The proxy combines:
        1. customer late-return behavior
        2. rental frequency
        3. rental-rate exposure
        4. category-level late-return behavior

    The resulting coefficient is data-derived and is intended for
    scenario simulation rather than causal inference.
    """

    # ---------------------------------------------------------
    # 1. Validate input
    # ---------------------------------------------------------

    if not rental_data:
        raise ValueError("rental_data is required.")

    if not film_data:
        raise ValueError("film_data is required.")

    # ---------------------------------------------------------
    # 2. Build film lookup
    # ---------------------------------------------------------

    film_lookup = {}

    for film in film_data:

        film_id = (
            film.get("film_id")
            or film.get("fid")
            or film.get("id")
        )

        if film_id is None:
            continue

        film_lookup[film_id] = film

    # ---------------------------------------------------------
    # 3. Customer-level behavior
    # ---------------------------------------------------------

    customer_stats = defaultdict(
        lambda: {
            "rentals": 0,
            "late": 0
        }
    )

    category_stats = defaultdict(
        lambda: {
            "rentals": 0,
            "late": 0
        }
    )

    rental_rates = []

    valid_rentals = 0

    # ---------------------------------------------------------
    # 4. Read rental behavior
    # ---------------------------------------------------------

    for rental in rental_data:

        customer_id = (
            rental.get("customer_id")
            or rental.get("customer")
            or rental.get("customerid")
        )

        film_id = (
            rental.get("film_id")
            or rental.get("film")
            or rental.get("fid")
        )

        # -----------------------------------------------------
        # Determine late status
        # -----------------------------------------------------

        late = rental.get("is_late")

        if late is None:

            late_days = (
                rental.get("late_days")
                or rental.get("days_late")
            )

            if late_days is not None:

                try:
                    late = float(late_days) > 0

                except (TypeError, ValueError):
                    late = None

        if late is None:

            return_date = rental.get("return_date")
            rental_date = rental.get("rental_date")

            rental_duration = (
                rental.get("rental_duration")
                or rental.get("duration")
            )

            if (
                return_date is not None
                and rental_date is not None
                and rental_duration is not None
            ):

                try:
                    actual_days = (
                        return_date - rental_date
                    ).days

                    late = (
                        actual_days
                        > int(rental_duration)
                    )

                except Exception:
                    late = None

        if late is None:
            continue

        late = bool(late)

        valid_rentals += 1

        # -----------------------------------------------------
        # Customer statistics
        # -----------------------------------------------------

        if customer_id is not None:

            customer_stats[customer_id]["rentals"] += 1

            if late:
                customer_stats[customer_id]["late"] += 1

        # -----------------------------------------------------
        # Film/category statistics
        # -----------------------------------------------------

        film = film_lookup.get(film_id)

        if film:

            category = (
                film.get("category")
                or film.get("name")
                or film.get("category_name")
                or "Unknown"
            )

            category_stats[category]["rentals"] += 1

            if late:
                category_stats[category]["late"] += 1

            rental_rate = film.get("rental_rate")

            if rental_rate is not None:

                try:
                    rental_rates.append(
                        float(rental_rate)
                    )

                except (TypeError, ValueError):
                    pass

    # ---------------------------------------------------------
    # 5. Basic validation
    # ---------------------------------------------------------

    if valid_rentals == 0:
        raise ValueError(
            "No valid rental behavior observations found."
        )

    if not rental_rates:
        raise ValueError(
            "No rental-rate observations found."
        )

    # ---------------------------------------------------------
    # 6. Overall late-return behavior
    # ---------------------------------------------------------

    total_late = sum(
        stats["late"]
        for stats in customer_stats.values()
    )

    total_customer_rentals = sum(
        stats["rentals"]
        for stats in customer_stats.values()
    )

    overall_late_rate = (
        total_late / total_customer_rentals
        if total_customer_rentals > 0
        else 0
    )

    # ---------------------------------------------------------
    # 7. Customer behavioral sensitivity
    # ---------------------------------------------------------
    #
    # We use observed dispersion in customer late-return rates.
    #
    # Customers whose behavior differs strongly from the overall
    # population provide more behavioral variation than customers
    # whose behavior is almost identical.
    #
    # This is a revealed-behavior proxy, NOT causal elasticity.
    # ---------------------------------------------------------

    customer_late_rates = []

    for stats in customer_stats.values():

        if stats["rentals"] <= 0:
            continue

        rate = (
            stats["late"]
            / stats["rentals"]
        )

        customer_late_rates.append(rate)

    if customer_late_rates:

        average_customer_late_rate = mean(
            customer_late_rates
        )

        behavioral_dispersion = mean(
            abs(
                rate
                - overall_late_rate
            )
            for rate in customer_late_rates
        )

    else:

        average_customer_late_rate = overall_late_rate
        behavioral_dispersion = 0.0

    # ---------------------------------------------------------
    # 8. Rental-rate distribution
    # ---------------------------------------------------------

    rental_rates = sorted(rental_rates)

    n = len(rental_rates)

    median_rental_rate = rental_rates[
        (n - 1) // 2
    ]

    q75_rental_rate = rental_rates[
        int(0.75 * (n - 1))
    ]

    q90_rental_rate = rental_rates[
        int(0.90 * (n - 1))
    ]

    # ---------------------------------------------------------
    # 9. Data-derived sensitivity coefficient
    # ---------------------------------------------------------
    #
    # The coefficient is constructed from observed behavior:
    #
    #   late-return intensity
    #   × behavioral dispersion
    #
    # We normalize by the observed rental-price level so that the
    # coefficient is dimensionless.
    #
    # No fixed 0.5 assumption is used.
    # ---------------------------------------------------------

    price_scale = median_rental_rate

    if price_scale <= 0:
        price_scale = 1.0

    sensitivity_coefficient = (
        overall_late_rate
        * (
            1.0
            + behavioral_dispersion
        )
    )

    sensitivity_coefficient = (
        sensitivity_coefficient
        / price_scale
    )

    # Keep numerical stability without imposing a business
    # assumption about the actual elasticity.
    sensitivity_coefficient = max(
        sensitivity_coefficient,
        0.0001
    )

    # ---------------------------------------------------------
    # 10. Data-derived fee benchmark
    # ---------------------------------------------------------
    #
    # Instead of saying "90th percentile is the ceiling",
    # use the observed rental-rate distribution and late-return
    # behavior to derive a behavioral burden factor.
    #
    # Higher late-return exposure permits a larger fee benchmark,
    # but the benchmark remains tied to observed rental prices.
    # ---------------------------------------------------------

    late_behavior_factor = (
        1.0 + overall_late_rate
    )

    fee_benchmark = (
        median_rental_rate
        * late_behavior_factor
    )

    # ---------------------------------------------------------
    # 11. Data-derived lower / upper benchmark
    # ---------------------------------------------------------

    fee_lower_bound = min(
        median_rental_rate,
        q75_rental_rate
    )

    fee_upper_bound = min(
        q90_rental_rate,
        fee_benchmark
    )

    if fee_upper_bound < fee_lower_bound:
        fee_upper_bound = fee_lower_bound

    # ---------------------------------------------------------
    # 12. Baseline rental count
    # ---------------------------------------------------------

    baseline_rentals = valid_rentals

    return {

        "estimable": True,

        "method": (
            "Revealed-behavior pricing proxy derived from "
            "observed Sakila rental and late-return behavior. "
            "The sensitivity coefficient is not a causal "
            "price elasticity because Sakila contains no "
            "historical variation in late-fee levels."
        ),

        # -----------------------------------------------------
        # Behavioral statistics
        # -----------------------------------------------------

        "behavior": {

            "overall_late_rate": round(
                overall_late_rate,
                6
            ),

            "average_customer_late_rate": round(
                average_customer_late_rate,
                6
            ),

            "behavioral_dispersion": round(
                behavioral_dispersion,
                6
            ),

            "customer_count": len(
                customer_stats
            ),

            "valid_rental_observations": valid_rentals
        },

        # -----------------------------------------------------
        # Pricing statistics
        # -----------------------------------------------------

        "pricing": {

            "min_rental_rate": round(
                min(rental_rates),
                2
            ),

            "median_rental_rate": round(
                median_rental_rate,
                2
            ),

            "q75_rental_rate": round(
                q75_rental_rate,
                2
            ),

            "q90_rental_rate": round(
                q90_rental_rate,
                2
            ),

            "max_rental_rate": round(
                max(rental_rates),
                2
            )
        },

        # -----------------------------------------------------
        # Simulation parameters
        # -----------------------------------------------------

        "simulation": {

            "behavioral_sensitivity": round(
                sensitivity_coefficient,
                6
            ),

            "baseline_rentals": baseline_rentals,

            "baseline_rental_rate": round(
                median_rental_rate,
                2
            )
        },

        # -----------------------------------------------------
        # Fee constraint
        # -----------------------------------------------------

        "fee_constraint": {

            "lower_bound": round(
                fee_lower_bound,
                2
            ),

            "upper_bound": round(
                fee_upper_bound,
                2
            ),

            "benchmark": round(
                fee_benchmark,
                2
            )
        }
    }
