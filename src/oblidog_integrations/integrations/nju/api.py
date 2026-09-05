"""Authenticated HTML client for the NJU Mobile invoice portal."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from http.cookiejar import CookieJar
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from bs4 import BeautifulSoup

from oblidog_integrations.integrations.nju.models import NjuInvoice

LOGIN_URL = "https://www.njumobile.pl/logowanie?backUrl=/mojekonto/faktury"
POST_URL = "https://www.njumobile.pl/logowanie?_DARGS=/profile-processes/login/login.jsp.portal-login-form"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


class NjuError(RuntimeError):
    """Raised when NJU Mobile cannot authenticate or provide invoice data."""


class NjuClient:
    """Fetch and parse invoices for one NJU Mobile account."""

    def __init__(
        self,
        *,
        phone: str,
        password: str,
        timeout: float = 30.0,
        opener_factory: Callable[..., Any] = build_opener,
    ) -> None:
        self._phone = phone
        self._password = password
        self._timeout = timeout
        self._opener_factory = opener_factory

    def fetch_invoices(self) -> list[NjuInvoice]:
        """Authenticate and return all invoices visible in the portal."""
        return parse_invoices(self._login_page())

    def _login_page(self) -> str:
        opener = self._opener_factory(HTTPCookieProcessor(CookieJar()))
        login_page = self._open(opener, Request(LOGIN_URL, headers=self._headers()))
        session_token = BeautifulSoup(login_page, "html.parser").find(
            "input", attrs={"name": "_dynSessConf"}
        )
        if session_token is None or not session_token.get("value"):
            raise NjuError("NJU Mobile login page did not provide a session token")

        payload = {
            "_dyncharset": "UTF-8",
            "_dynSessConf": session_token["value"],
            "/ptk/sun/login/formhandler/LoginFormHandler.backUrl": "/mojekonto/faktury",
            "_D:/ptk/sun/login/formhandler/LoginFormHandler.backUrl": "+",
            "/ptk/sun/login/formhandler/LoginFormHandler.hashMsisdn": "",
            "_D:/ptk/sun/login/formhandler/LoginFormHandler.hashMsisdn": "+",
            "phone-input": self._phone,
            "_D:phone-input": "+",
            "password-form": self._password,
            "_D:password-form": "+",
            "login-submit": "zaloguj+się",
            "_D:login-submit": "+",
            "_DARGS": "/profile-processes/login/login.jsp.portal-login-form",
        }
        request = Request(
            POST_URL,
            data=urlencode(payload).encode(),
            headers={
                **self._headers(),
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://www.njumobile.pl",
                "Referer": LOGIN_URL,
            },
        )
        return self._open(opener, request)

    def _open(self, opener: Any, request: Request) -> str:
        try:
            with opener.open(request, timeout=self._timeout) as response:
                return response.read().decode("utf-8")
        except (HTTPError, URLError, UnicodeDecodeError) as error:
            raise NjuError("NJU Mobile request failed") from error

    @staticmethod
    def _headers() -> dict[str, str]:
        return {"User-Agent": USER_AGENT}


def parse_invoices(html: str) -> list[NjuInvoice]:
    """Parse invoice rows from an authenticated NJU Mobile invoices page."""
    soup = BeautifulSoup(html, "html.parser")
    invoices: list[NjuInvoice] = []
    for row in soup.select("tr[id^='id_abc-']"):
        fields = {cell.get("data-title"): cell for cell in row.select("td[data-title]")}
        if not fields:
            continue
        try:
            invoices.append(
                NjuInvoice(
                    document_id=_document_id(fields["nr dokumentu"]),
                    issue_date=_date(fields["data wystawienia"].get_text()),
                    due_date=_date(fields["termin płatności"].get_text()),
                    paid_amount=_amount(fields["kwota zapłacona"].get_text()),
                    payable_amount=_amount(fields["do zapłaty"].get_text()),
                    accounting_period=fields["za okres"].get_text(strip=True),
                    status=fields["status"].get_text(strip=True),
                )
            )
        except (KeyError, ValueError, InvalidOperation) as error:
            raise NjuError("NJU Mobile returned an invalid invoice row") from error
    return invoices


def invoices_for_current_period(
    invoices: list[NjuInvoice], *, now: datetime
) -> list[NjuInvoice]:
    """Return invoices whose portal period matches the supplied month."""
    period = now.strftime("%m.%Y")
    return [invoice for invoice in invoices if invoice.accounting_period == period]


def _document_id(cell: Any) -> str:
    anchor = cell.find("a")
    if anchor is not None and anchor.get("id"):
        return str(anchor["id"]).rsplit("-", maxsplit=1)[-1]
    return cell.get_text(strip=True)


def _date(value: str) -> date:
    day, month, year = value.strip().split(".")
    return date(int(year), int(month), int(day))


def _amount(value: str) -> Decimal:
    normalized = value.replace("\xa0", " ").strip().replace(",", ".")
    return Decimal(normalized.split()[0])
