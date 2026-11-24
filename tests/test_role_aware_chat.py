import json
import unittest

from gui.data import BOOKS
from gui.llm import financial_answer, system_prompt
from gui.reports import financial_report


class TestFinancialReport(unittest.TestCase):

    def setUp(self):
        self.orders = [
            {
                "placed": "2026-11-24",
                "total": 90.0,
                "discount_amount": 10.0,
                "book_ids": [BOOKS[0].id, BOOKS[1].id],
            },
            {
                "placed": "2026-11-24",
                "total": 45.0,
                "discount_amount": 5.0,
                "book_ids": [BOOKS[0].id],
            },
        ]

        self.users = [{"role": "RC"}, {"role": "VC"}]
        self.report = financial_report(self.orders, self.users)

    def test_total_orders(self):
        self.assertEqual(self.report["total_orders"], 2)

    def test_total_revenue(self):
        self.assertEqual(self.report["total_sales"], 135.0)

    def test_total_discounts(self):
        self.assertEqual(self.report["total_discounts"], 15.0)

    def test_books_sold(self):
        self.assertEqual(self.report["books_sold"], 3)

    def test_orders_by_day(self):
        self.assertEqual(
            self.report["orders_by_day"],
            {"2026-11-24": 2},
        )

    def test_top_selling_books(self):
        top = self.report["top_selling_books"][0]
        self.assertEqual(top["title"], BOOKS[0].title)
        self.assertEqual(top["quantity"], 2)

    def test_customer_counts(self):
        self.assertEqual(self.report["vip_customers"], 1)
        self.assertEqual(self.report["registered_customers"], 1)

    def test_empty_report(self):
        report = financial_report([], [])
        self.assertEqual(report["total_sales"], 0)
        self.assertEqual(report["total_orders"], 0)
        self.assertEqual(report["top_selling_books"], [])


class TestRoleAwareChat(unittest.TestCase):

    def setUp(self):
        self.report = {
            "total_orders": 2,
            "total_sales": 135.0,
            "total_discounts": 15.0,
            "books_sold": 3,
        }

    def test_super_user_financial_access(self):
        prompt = system_prompt(
            BOOKS,
            role="SU",
            financial_summary=self.report,
        )
        self.assertIn("Bookstore financial report:", prompt)
        self.assertIn(
            json.dumps(self.report, separators=(",", ":")),
            prompt,
        )

    def test_non_super_user_financial_privacy(self):
        for role in ("RC", "VC", "VS"):
            with self.subTest(role=role):
                prompt = system_prompt(
                    BOOKS,
                    role=role,
                    financial_summary=self.report,
                )
                self.assertNotIn(
                    "Bookstore financial report:", prompt
                )
                self.assertNotIn(
                    json.dumps(self.report, separators=(",", ":")),
                    prompt,
                )

    def test_super_user_revenue_answer(self):
        answer = financial_answer(
            "What was total revenue?",
            "SU",
            self.report,
        )
        self.assertIn("$135.00", answer)
        self.assertNotIn("$150.00", answer)

    def test_unauthorized_revenue_answer(self):
        for role in ("RC", "VC", "VS"):
            with self.subTest(role=role):
                answer = financial_answer(
                    "What was total revenue?",
                    role,
                    self.report,
                )
                self.assertIn("restricted", answer)
                self.assertNotIn("$135.00", answer)

    def test_visitor_catalog_access(self):
        prompt = system_prompt(BOOKS, role="VS")
        self.assertIn(BOOKS[0].title, prompt)
        self.assertIn(BOOKS[0].price_text, prompt)
        self.assertIn("public catalog only", prompt)

    def test_visitor_purchase_privacy(self):
        prompt = system_prompt(
            BOOKS,
            purchased=[BOOKS[0]],
            role="VS",
        )
        self.assertNotIn(
            "The customer has already bought:", prompt
        )
        self.assertNotIn(
            "Customer billing information:", prompt
        )

    def test_normal_book_question(self):
        self.assertIsNone(
            financial_answer("Recommend a book", "VS")
        )


if __name__ == "__main__":
    unittest.main()