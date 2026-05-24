# -*- coding: utf-8 -*-
"""
naklady_engine.py — výpočetní jádro modulu Náklady řízení.

Extrahováno z OSspravce (autor: Mgr. Pavel Tureček, OS Pardubice).
Pure-Python výpočetní engine pro web demo (Streamlit).

Odstraněno proti původnímu OSspravce modulu:
- file I/O (rates.json, travel.json) — pro web stačí DEFAULT_RATES inline
- Tkinter messagebox volání — nahrazeno print()
- save_*_to_file metody — web nepersistujemě

Závislosti: jen Python standard library.
"""
from __future__ import annotations

import copy
import math
import json
import locale
from datetime import datetime, date, timedelta


def atomic_json_write(*args, **kwargs):
    """Stub pro web verze — engine žádné persistování nedělá."""
    pass


# Placeholder pro file constants — web verze je nepoužívá
RATES_FILENAME = "rates.json"
TRAVEL_DATA_FILENAME = "travel.json"


class _FakeMessagebox:
    """Stub pro web — Tkinter messagebox volání jen vypíšeme do logu."""
    @staticmethod
    def showinfo(title, msg, **kw):
        print(f"[info] {title}: {msg}")

    @staticmethod
    def showwarning(title, msg, **kw):
        print(f"[warn] {title}: {msg}")

    @staticmethod
    def showerror(title, msg, **kw):
        print(f"[error] {title}: {msg}")


messagebox = _FakeMessagebox()


# ═══════════════════════════════════════════════════════════════
# CalculationEngine — výpočetní jádro
# ═══════════════════════════════════════════════════════════════

class CalculationEngine:
    def __init__(self):
        self.VAT_RATE = 0.21
        self.LEGAL_ACTS = {
            "převzetí a příprava zastoupení": {"type": "full"},
            "výzva k plnění nikoli jednoduchá": {"type": "full"},
            "jednoduchá výzva k plnění": {"type": "half"},
            "sepis žaloby": {"type": "full"},
            "podání ve věci samé": {"type": "full"},
            "zpětvzetí žaloby": {"type": "full"},
            "podání odvolání / dovolání": {"type": "full"},
            "účast na jednání soudu": {"type": "full"},
            "účast při přípravném jednání": {"type": "half"},
            "jednání s protistranou": {"type": "full"},
            "další porada s klientem (>1h)": {"type": "full"},
            "návrh na předběžné opatření (po zahájení)": {"type": "half"},
        }
        self.FORMULARY_ACTS = [
            "převzetí a příprava zastoupení",
            "jednoduchá výzva k plnění",
            "výzva k plnění nikoli jednoduchá",
            "sepis žaloby",
        ]

        self.travel_data = []
        self._load_travel_data_from_file()

        # Výchozí data pro případ, že chybí soubor (zjednodušená struktura)
        self.DEFAULT_RATES = [
            {
                "obdobi_od": "01.01.2026",
                "obdobi_do": "31.12.9999",
                "cislo_vyhlasky": "DOPLNIT/2025 Sb.",
                "palivo_amortizace": {
                    "benzín": 35.80,
                    "nafta": 34.70,
                    "elektřina": 7.70,
                    "amortizace": 5.80,
                }
            },
            {
                "obdobi_od": "01.01.2025",
                "obdobi_do": "31.12.2025",
                "cislo_vyhlasky": "475/2024 Sb.",
                "palivo_amortizace": {
                    "benzín": 35.80,
                    "nafta": 34.70,
                    "elektřina": 7.70,
                    "amortizace": 5.80,
                }
            }
        ]
        self.rates_data = []
        self.load_rates_from_file()

    def load_rates_from_file(self):
        """Web verze: žádný file load, jen použij DEFAULT_RATES."""
        self.rates_data = copy.deepcopy(self.DEFAULT_RATES)


    def save_rates_to_file(self, show_success=True):
        """Web verze: no-op (žádné persistování)."""
        return


    def _get_default_travel_data(self):
        return [
            {"mesto": "Hradec Králové", "vzdalenost_km": 21, "cas_min": 25},
            {"mesto": "Praha", "vzdalenost_km": 104, "cas_min": 90},
            {"mesto": "Brno", "vzdalenost_km": 138, "cas_min": 120},
            {"mesto": "Ostrava", "vzdalenost_km": 240, "cas_min": 180},
            {"mesto": "Plzeň", "vzdalenost_km": 198, "cas_min": 150},
            {"mesto": "Liberec", "vzdalenost_km": 118, "cas_min": 100},
        ]

    def _load_travel_data_from_file(self):
        """Web verze: default travel data only."""
        self.travel_data = self._get_default_travel_data()


    def _save_travel_data_to_file(self, show_success=True):
        """Web verze: no-op (žádné persistování)."""
        return


    def update_travel_data_entry(self, city_name, new_dist, new_time):
        city_found = False
        for entry in self.travel_data:
            if entry["mesto"].lower() == city_name.lower():
                entry["vzdalenost_km"] = new_dist
                entry["cas_min"] = new_time
                city_found = True
                break
        if not city_found:
            self.travel_data.append(
                {"mesto": city_name, "vzdalenost_km": new_dist, "cas_min": new_time}
            )
        self._save_travel_data_to_file(show_success=False)

    def get_rates_for_date(self, date_of_act):
        """
        Načte základní data z JSONu (palivo, vyhláška) a dynamicky doplní
        hardcoded hodnoty (paušály, NZČ, specifické tarify) podle data.
        """
        found_rates = None
        # 1. Najít odpovídající záznam v JSONu (pro palivo a vyhlášku)
        for rates in self.rates_data:
            try:
                start_date = datetime.strptime(rates["obdobi_od"], "%d.%m.%Y")
                end_date = datetime.strptime(rates["obdobi_do"], "%d.%m.%Y")
                if start_date <= date_of_act <= end_date:
                    found_rates = copy.deepcopy(rates)
                    break
            except (ValueError, KeyError):
                continue
        
        if not found_rates and self.rates_data:
            found_rates = copy.deepcopy(self.rates_data[-1])
        
        if not found_rates:
            # Fallback, pokud je JSON prázdný
            found_rates = copy.deepcopy(self.DEFAULT_RATES[0])

        # 2. Doplnit Hardcoded logiku pro rok 2025+ vs starší
        is_post_2025 = date_of_act >= datetime(2025, 1, 1)

        if is_post_2025:
            # Sazby od 1.1.2025
            found_rates["pausal_normal"] = 450
            found_rates["pausal_formular"] = 100
            found_rates["ztrata_casu_sazba"] = 150
            found_rates["specific_tariffs"] = {
                "neurčitelná hodnota": 30000,
                "opatrovnické věci, sociální zabezpečení": 10000,
                "určení neplatnosti, ochrana osobnosti (bez náhrady)": 65000,
                "osobnostní práva (s náhradou), obchodní společnosti": 113000,
                "ústavní stížnost": 128000,
            }
        else:
            # Staré sazby (do 31.12.2024)
            found_rates["pausal_normal"] = 300
            found_rates["pausal_formular"] = 100
            found_rates["ztrata_casu_sazba"] = 100
            found_rates["specific_tariffs"] = {
                "neurčitelná hodnota": 10000,
                "opatrovnické věci, sociální zabezpečení": 5000,
                "určení neplatnosti, ochrana osobnosti (bez náhrady)": 35000,
                "osobnostní práva (s náhradou), obchodní společnosti": 50000,
                "ústavní stížnost": 35000,
            }

        return found_rates

    def calculate_court_fee(self, amount, fee_type):
        base = math.ceil(amount / 10) * 10
        if fee_type == "full":
            if base <= 20000:
                return 1000.0
            if base <= 40000000:
                return float(math.ceil(base * 0.05))
            return 2000000.0 + math.ceil((base - 40000000) * 0.01)
        elif fee_type == "reduced":
            if amount <= 10000:
                return 400.0
            if amount <= 20000:
                return 800.0
            return float(math.ceil(amount * 0.04))
        return 0.0

    def get_fee_per_act(self, act_name, tariff_value, date_of_act, proc_type):
        act_base_name = act_name.split(" (")[0]
        act_info = self.LEGAL_ACTS.get(act_base_name, {"type": "full"})
        
        # Logika pro formulářové žaloby (změna od 2025)
        if proc_type == "form" and act_base_name in self.FORMULARY_ACTS:
            is_post_2025 = date_of_act >= datetime(2025, 1, 1)
            if is_post_2025:
                if tariff_value <= 10000:
                    return 300.0
                if tariff_value <= 30000:
                    return 400.0
                if tariff_value <= 50000:
                    return 700.0
            else:
                if tariff_value <= 10000:
                    return 200.0
                if tariff_value <= 30000:
                    return 300.0
                if tariff_value <= 50000:
                    return 500.0
        
        # Standardní tarif
        if tariff_value <= 500:
            base_fee = 300.0
        elif tariff_value <= 1000:
            base_fee = 500.0
        elif tariff_value <= 5000:
            base_fee = 1000.0
        elif tariff_value <= 10000:
            base_fee = 1500.0
        elif tariff_value <= 200000:
            base_fee = 1500.0 + (math.ceil((tariff_value - 10000) / 1000) * 40)
        elif tariff_value <= 10000000:
            base_fee = 9100.0 + (math.ceil((tariff_value - 200000) / 10000) * 40)
        else:
            base_fee = 48300.0 + (math.ceil((tariff_value - 10000000) / 100000) * 40)
            
        if act_info["type"] == "half":
            return base_fee / 2
        return float(base_fee)

    def calculate_all(self, data):
        tariff_value = data.get("tariff_value", 0)
        awarded_amount = data.get("awarded_amount", 0)
        
        if data.get("manual_success_pct") is not None:
            plaintiff_success_pct = data["manual_success_pct"]
        else:
            if data.get("defendant_won", False):
                plaintiff_success_pct = 0
            else:
                if tariff_value > 0:
                    plaintiff_success_pct = (awarded_amount / tariff_value) * 100
                else:
                    plaintiff_success_pct = 100 if awarded_amount >= 0 else 0

        net_success_pct = plaintiff_success_pct - (100 - plaintiff_success_pct)
        (
            total_fee_base,
            total_overhead,
            total_travel_expense,
            total_time_loss_comp,
            total_other_expenses,
            total_vat,
        ) = (0, 0, 0, 0, 0, 0)
        # V13.4.28e+: rozdělené hotové výdaje pro lepší odůvodnění.
        # Pavel viděl jen sumu „cestovné" a nevěděl breakdown jízdné/parkovné.
        total_jizdne = 0.0
        total_parkovne = 0.0

        global_manual_fee = data.get("global_manual_fee")
        manual_paragraph = data.get("manual_paragraph")

        if data.get("unrepresented_party", False):
            # V13.4.28e+: NEZASTOUPENÝ ÚČASTNÍK = shortcut „označ všechny úkony
            # jako provedené před převzetím zastoupení". Reálná logika je
            # smíšený režim — pro Pavla je to jen rychlá volba „tickni vše".
            # Skutečný výpočet probíhá jednotně přes per-úkon flag níže.
            pass

        formular_overhead_count = 0
        normal_overhead_count = 0
        # V13.4.28e+: počítadla pro úkony před převzetím zastoupení
        # (paušál podle § 151 odst. 3 OSŘ + vyhlášky 254/2015 Sb.).
        # Sazba: do 31.12.2024 = 300 Kč, od 1.1.2025 = 450 Kč.
        # Hodnota se bere z `rates.pausal_normal` (= stejná částka jako
        # advokátní režijní paušál podle § 13 odst. 4 vyhl. 177/1996).
        before_repr_count = 0
        is_unrep = bool(data.get("unrepresented_party", False))
        for act in data["performed_acts"]:
            rates = self.get_rates_for_date(act["date"])
            if not rates:
                continue

            # V13.4.28e+: before_representation = explicitní flag, NEBO
            # derivované z NEZASTOUPENÝ ÚČASTNÍK (zaškrtne všechny úkony).
            is_before_repr = is_unrep or bool(act.get("before_representation", False))

            # ── ÚKON PŘED PŘEVZETÍM ZASTOUPENÍ — paušál podle data ──
            if is_before_repr:
                # V13.4.28e+ (poslední session): místo hardcoded 300 použít
                # sazbu z rates.pausal_normal (300 do 31.12.2024, 450 od
                # 1.1.2025) — automatika podle data úkonu.
                nezast_sazba = float(rates.get("pausal_normal", 300))
                total_fee_base += nezast_sazba
                before_repr_count += 1
                # Cestovné a hotové výdaje ANO (i nezastoupený má nárok),
                # ale BEZ NZČ (náhrada za ztrátu času = jen advokát) a BEZ
                # režijního paušálu (jen § 13 odst. 4 vyhlášky 177/1996 Sb.
                # = advokátní benefit).
                if act.get("travel"):
                    travel_info = act.get("travel")
                    breakdown = self.calculate_travel_cost_breakdown(
                        travel_info, act["date"]
                    )
                    if breakdown:
                        total_travel_expense += breakdown["total"]
                    j = travel_info.get("jizdne", 0.0)
                    p = travel_info.get("parkovne", 0.0)
                    total_jizdne += j
                    total_parkovne += p
                    total_other_expenses += j + p
                continue

            # ── ÚKON ADVOKÁTA — tarif + režijní paušál + DPH ──
            if act.get("manual_fee") is not None:
                total_fee_base += act["manual_fee"]
            elif global_manual_fee is not None:
                total_fee_base += global_manual_fee
            else:
                act_tariff_value = act.get("tariff_value", tariff_value)
                total_fee_base += self.get_fee_per_act(
                    act["name"], act_tariff_value, act["date"], data["proc_type"]
                )

            act_base_name = act["name"].split(" (")[0]
            if data["proc_type"] == "form" and act_base_name in self.FORMULARY_ACTS:
                total_overhead += rates.get("pausal_formular", 100)
                formular_overhead_count += 1
            else:
                total_overhead += rates.get("pausal_normal", 300)
                normal_overhead_count += 1

            if act.get("travel"):
                travel_info = act.get("travel")
                breakdown = self.calculate_travel_cost_breakdown(
                    travel_info, act["date"]
                )
                if breakdown:
                    total_travel_expense += breakdown["total"]
                total_time_loss_comp += self.calculate_time_loss_comp(
                    travel_info, act["date"]
                )
                j = travel_info.get("jizdne", 0.0)
                p = travel_info.get("parkovne", 0.0)
                total_jizdne += j
                total_parkovne += p
                total_other_expenses += j + p

        if data["modification"] == "half":
            total_fee_base /= 2
        elif data["modification"] == "treble":
            total_fee_base *= 3

        # DPH — z (tarif + režijní paušál + cestovné + NZČ); pokud byly
        # všechny úkony před zastoupením, total_fee_base = N × 300 a
        # paušál 300 Kč není odměna advokáta. Aby DPH nebyla aplikována
        # na paušální náhradu (která není odměnou plátce DPH), počítáme
        # ji jen z advokátní části:
        advocate_fee_base = total_fee_base - (before_repr_count * 300.0)
        # (advokátní část = celkem – „paušální 300 Kč úkony";
        #  ostatní položky se aplikují na DPH stejně jako dosud.)
        subtotal_for_vat = (
            advocate_fee_base
            + total_overhead
            + total_travel_expense
            + total_time_loss_comp
        )
        if data.get("vat_on_tickets", False):
            subtotal_for_vat += total_other_expenses
        total_vat = subtotal_for_vat * self.VAT_RATE if data["is_vat_payer"] else 0

        final_court_fee = data["court_fee_paid"]
        # V13.4.28e+: doměření SOP — Pavel zaškrtl „placeno + doměřit"
        # → court_fee_paid = X (snížený, EPR), court_fee_domer = Y (plný).
        # Doměření = Y − X (= rozdíl, který soud ukládá doplatit).
        # Do nákladů řízení vstupuje plný poplatek Y (= co měl žalobce
        # zaplatit, kdyby EPR vydán nebyl).
        court_fee_full = float(data.get("court_fee_domer", 0) or 0)
        court_fee_domer_amount = 0.0
        if data.get("sop_volba") == "domer" and court_fee_full > data["court_fee_paid"]:
            court_fee_domer_amount = court_fee_full - data["court_fee_paid"]
            final_court_fee = court_fee_full  # = X + (Y−X) = Y
        if data.get("refund_sop", False):
            non_refundable_part = max(data["court_fee_paid"] * 0.20, 1000)
            final_court_fee = non_refundable_part

        subtotal_advocate = (
            total_fee_base
            + total_overhead
            + total_travel_expense
            + total_time_loss_comp
        )
        grand_total = (
            subtotal_advocate + total_vat + final_court_fee + total_other_expenses
        )

        if data.get("defendant_won", False):
            claimable_amount = grand_total
        else:
            claimable_amount = (
                grand_total * (net_success_pct / 100) if net_success_pct > 0 else 0
            )

        return {
            "tariff_value": tariff_value,
            "awarded_amount": awarded_amount,
            "proc_type": data["proc_type"],
            "modification": data["modification"],
            "total_fee_base": total_fee_base,
            "total_overhead": total_overhead,
            "total_travel_expense": total_travel_expense,
            "total_time_loss_comp": total_time_loss_comp,
            "total_other_expenses": total_other_expenses,
            # V13.4.28e+: rozdělené hotové výdaje pro detailní odůvodnění
            "total_jizdne": total_jizdne,
            "total_parkovne": total_parkovne,
            "court_fee_paid": final_court_fee,
            "original_court_fee": data["court_fee_paid"],
            # V13.4.28e+: doměření info — pro text odůvodnění
            "sop_volba": data.get("sop_volba", "full"),
            "court_fee_domer": court_fee_domer_amount,   # = Y − X
            "court_fee_plny":  court_fee_full,           # = Y
            "court_fee_placeno": data["court_fee_paid"], # = X
            # VS + účet pro samostatný výrok o doměření
            "domer_vs":   _parse_vs_from_spzn(data.get("spis_znacka", "")),
            "domer_ucet": ACCOUNT_NUMBERS.get("soudní poplatky",
                                                 "3703-625561/0710"),
            "subtotal_advocate": subtotal_advocate,
            "total_vat": total_vat,
            "grand_total": grand_total,
            "claimable_amount": claimable_amount,
            "net_success_pct": net_success_pct,
            "plaintiff_success_pct": plaintiff_success_pct,
            "refund_sop": data.get("refund_sop", False),
            "defendant_won": data.get("defendant_won", False),
            "plaintiff_is_woman": data.get("plaintiff_is_woman", False),
            "defendant_is_woman": data.get("defendant_is_woman", False),
            "unrepresented_party": data.get("unrepresented_party", False),
            # V13.4.28e+: počet úkonů provedených před převzetím zastoupení
            # — pro odůvodnění (rozdělení textu na 2 části).
            "before_repr_count": locals().get("before_repr_count", 0),
            "accessory_failure": data.get("accessory_failure", False),
            "global_manual_fee": global_manual_fee,
            "manual_paragraph": manual_paragraph
        }

    def calculate_travel_cost_breakdown(self, travel_data, act_date):
        if not travel_data:
            return None
        # V13.4.28e+: vlak mode — zástupce přijel vlakem.
        # Žádné palivo, žádná amortizace. Jen NZČ + jízdné se počítají
        # zvlášť (NZČ v calculate_time_loss_comp, jízdné v aktu).
        if travel_data.get("mode") == "vlak":
            return {
                "fuel_cost": 0.0,
                "amort_cost": 0.0,
                "total": 0.0,
                "fuel_price": 0.0,
                "amort_rate": 0.0,
                "total_dist": 0,
                "mode": "vlak",
            }
        rates = self.get_rates_for_date(act_date)
        if not rates:
            return None
        fuel_amort_rates = rates.get("palivo_amortizace", rates.get("fuel_amort", {}))
        # V13.4.28e+ #19: Pokud je v travel_data doložená cena (= účtenka),
        # má přednost před vyhláškovou cenou. Legitimní postup dle § 158 OSŘ —
        # advokát doloží reálnou cenu paliva, počítá se s tou.
        fuel_price_manual = travel_data.get("fuel_price_manual")
        fuel_price_source = "vyhlaska"
        try:
            if fuel_price_manual is not None and float(fuel_price_manual) > 0:
                fuel_price = float(fuel_price_manual)
                fuel_price_source = "manual"   # = doložená účtenka
            else:
                fuel_price = fuel_amort_rates.get(travel_data["fuel_type"], 0)
        except (ValueError, TypeError):
            fuel_price = fuel_amort_rates.get(travel_data["fuel_type"], 0)
        amort_rate = fuel_amort_rates.get("amortizace", 0)
        total_dist = travel_data.get("distance_km", 0) * 2
        consumption = travel_data.get("consumption", 0)
        fuel_cost = (total_dist / 100) * consumption * fuel_price
        amort_cost = total_dist * amort_rate
        return {
            "fuel_cost": fuel_cost,
            "amort_cost": amort_cost,
            "total": fuel_cost + amort_cost,
            "fuel_price": fuel_price,
            "fuel_price_source": fuel_price_source,  # V13.4.28e+ #19
            "amort_rate": amort_rate,
            "total_dist": total_dist,
            "mode": "auto",
        }

    def calculate_time_loss_comp(self, travel_data, act_date):
        if not travel_data:
            return 0
        rates = self.get_rates_for_date(act_date)
        if not rates:
            return 0
        total_time_min = travel_data.get("time_min", 0) * 2
        half_hours = math.ceil(total_time_min / 30) if total_time_min > 0 else 0
        return half_hours * rates["ztrata_casu_sazba"]

    def format_currency(self, value, with_unit=True):
        if value is None:
            return "0" + (" Kč" if with_unit else "")
        try:
            formatted_val = locale.format_string("%.2f", value, grouping=True).replace(
                "\xa0", " "
            )
            if value == int(value):
                formatted_val = locale.format_string(
                    "%d", int(value), grouping=True
                ).replace("\xa0", " ")

            return formatted_val + (" Kč" if with_unit else "")
        except (ValueError, TypeError):
            return "Chyba"

    def generate_legal_text(self, r, performed_acts):
        f = self.format_currency
        f_num = lambda v: self.format_currency(v, with_unit=False)
        format_date_short = lambda d: f"{d.day}. {d.month}. {d.year}"
        is_full_success = abs(r["plaintiff_success_pct"] - 100) < 0.01

        if r.get("plaintiff_is_woman", False):
            plaintiff = {
                "nominative": "žalobkyně",
                "genitive": "žalobkyně",
                "dative": "žalobkyni",
                "instrumental": "žalobkyní",
                "possessive": "jejího",
                "is_woman": True,
            }
        else:
            plaintiff = {
                "nominative": "žalobce",
                "genitive": "žalobce",
                "dative": "žalobci",
                "instrumental": "žalobcem",
                "possessive": "jeho",
                "is_woman": False,
            }

        if r.get("defendant_is_woman", False):
            defendant = {
                "nominative": "žalovaná",
                "genitive": "žalované",
                "dative": "žalované",
                "instrumental": "žalovanou",
                "possessive": "jejího",
                "is_woman": True,
            }
        else:
            defendant = {
                "nominative": "žalovaný",
                "genitive": "žalovaného",
                "dative": "žalovanému",
                "instrumental": "žalovaným",
                "possessive": "jeho",
                "is_woman": False,
            }

        if r.get("defendant_won", False):
            winning_party = defendant
            losing_party = plaintiff
        else:
            winning_party = plaintiff
            losing_party = defendant

        claimable_amount_str = f(r["claimable_amount"])

        # V13.4.28e+: STANDARD VĚTEV — sjednocená pro všechny scénáře.
        # Pavel: "pokud je účastník nezastoupen a pak zastoupen, tak je to
        # normálně sečitatelné". NEZASTOUPENÝ ÚČASTNÍK je shortcut, který
        # zaškrtne všechny per-úkon flagy `before_representation` (= úkony
        # provedené před převzetím zastoupení). Skutečná logika = aditivní:
        #   SOP + úkony před zast. (paušál 300 Kč) + úkony advokáta
        #   (tarif + režijní paušál + DPH) + hotové výdaje (cestovné).
        # NZČ se NEPOČÍTÁ pro úkony před zastoupením (advokátní benefit).
        is_unrep_global = bool(r.get("unrepresented_party", False))
        # dynamicky povinen/povinna podle pohlaví losing party
        # ("Žalovaný je povinen" × "Žalovaná je povinna" × "Žalobce je povinen"
        # × "Žalobkyně je povinna").
        losing_povinen = "povinna" if losing_party.get("is_woman") else "povinen"
        # V13.4.28e+: pokud jsou VŠECHNY úkony před převzetím zastoupení
        # (= účastník je úplně nezastoupený), výrok NEOBSAHUJE „k rukám
        # zástupce" (zástupce neexistuje).
        all_before_repr = bool(performed_acts) and all(
            is_unrep_global or bool(act.get("before_representation"))
            for act in performed_acts
        )
        if all_before_repr:
            verdict_proposal = (
                "NÁVRH VÝROKU\n"
                "---------------------------------\n"
                f"{losing_party['nominative'].capitalize()} je {losing_povinen} nahradit {winning_party['dative']} do tří dnů od právní moci tohoto výroku "
                f"náklady řízení v částce {claimable_amount_str}."
            )
        else:
            verdict_proposal = (
                "NÁVRH VÝROKU\n"
                "---------------------------------\n"
                f"{losing_party['nominative'].capitalize()} je {losing_povinen} nahradit {winning_party['dative']} k rukám {winning_party['possessive']} zástupce do tří dnů od právní moci tohoto výroku "
                f"náklady řízení v částce {claimable_amount_str}."
            )

        justification_sentences = []
        if r.get("defendant_won", False):
            paragraph_osr = "142 odst. 1"
        else:
            paragraph_osr = "142 odst. 1" if is_full_success else "142 odst. 2"

        justification_sentences.append(
            f"O nákladech řízení soud rozhodl dle ustanovení § {paragraph_osr} občanského soudního řádu."
        )

        cost_clauses = []
        # V13.4.28e+ #9: pokud doměřujeme, court_fee_paid je Y (plná částka
        # po doměření) — Pavel chce v odůvodnění explicitně poznamenat
        # „(výše po doměření)", aby protistrana hned věděla.
        is_domer = (r.get("sop_volba") == "domer" and
                      r.get("court_fee_domer", 0) > 0)
        domer_note = " (výše po doměření)" if is_domer else ""
        if r.get("refund_sop", False):
            cost_clauses.append(
                f"zaplaceným soudním poplatkem ve výši {f(r['court_fee_paid'])}{domer_note} (část poplatku, kterou dle § 10 odst. 4 zákona o soudních poplatcích nelze vrátit)"
            )
        elif r["court_fee_paid"] > 0:
            cost_clauses.append(
                f"zaplaceným soudním poplatkem ve výši {f(r['court_fee_paid'])}{domer_note}"
            )

        acts_by_fee_and_paragraph = {}
        # V13.4.28e+: úkony před převzetím zastoupení sbíráme separátně
        # — pro samostatnou clause v odůvodnění (paušál 300/450 Kč).
        # is_unrep_global = True znamená že VŠECHNY úkony jsou před zast.
        # V13.4.28e+ (poslední session): ukládáme TUPLE (name, sazba),
        # aby mix dat 2024+2025 dokázal text rozdělit do dvou clauses
        # (300 Kč pro úkony do 31.12.2024, 450 Kč pro od 1.1.2025).
        before_repr_acts = []  # list[tuple[name:str, sazba:float]]
        for act in performed_acts:
            act_base_name = act["name"].split(" (")[0]

            # V13.4.28e+: úkony před převzetím zastoupení mají paušál
            # podle § 151 odst. 3 OSŘ + vyhlášky 254/2015 Sb.
            # Sazba: 300 Kč do 31.12.2024, 450 Kč od 1.1.2025.
            if is_unrep_global or act.get("before_representation"):
                try:
                    r_act = self.get_rates_for_date(act["date"])
                    sazba = float(r_act.get("pausal_normal", 300))
                except Exception:
                    sazba = 300.0
                before_repr_acts.append((act_base_name, sazba))
                continue

            if act.get("manual_fee") is not None:
                fee = float(act["manual_fee"])
            elif r.get("global_manual_fee") is not None:
                fee = r["global_manual_fee"]
            else:
                act_tariff_value = act.get("tariff_value", r["tariff_value"])
                fee = self.get_fee_per_act(
                    act["name"], act_tariff_value, act["date"], r["proc_type"]
                )

            paragraph = "§ 7"
            if r.get("manual_paragraph") and r.get("global_manual_fee") is not None and act.get("manual_fee") is None:
                paragraph = f"§ {r['manual_paragraph']}"
            elif r["proc_type"] == "form" and act_base_name in self.FORMULARY_ACTS:
                paragraph = "§ 14b"

            key = (fee, paragraph)
            if key not in acts_by_fee_and_paragraph:
                acts_by_fee_and_paragraph[key] = []
            acts_by_fee_and_paragraph[key].append(act_base_name)

        # --- LOGIKA PRO ZKRATKU VYHLÁŠKY ---
        vyhlaska_defined = False

        # V13.4.28e+: Před advokátními úkony — clause pro úkony provedené
        # účastníkem osobně před převzetím zastoupení (§ 151 odst. 3 OSŘ).
        # V13.4.28e+ (poslední session): rozdělit do clauses podle sazby
        # (300 Kč pro úkony do 31.12.2024, 450 Kč pro od 1.1.2025).
        if before_repr_acts:
            # Seskupit podle sazby: {300.0: [names…], 450.0: [names…]}
            by_sazba = {}
            for name, sazba in before_repr_acts:
                by_sazba.setdefault(sazba, []).append(name)

            # Vyšší sazba první (modernější úkony nahoru)
            for sazba in sorted(by_sazba.keys(), reverse=True):
                names = by_sazba[sazba]
                n = len(names)
                # Český plurál: 1 = úkon, 2-4 = úkony, 5+ = úkonů
                if n == 1:
                    ukon_word = "úkon"
                    provedeny_word = "provedený"
                elif n in (2, 3, 4):
                    ukon_word = "úkony"
                    provedeny_word = "provedené"
                else:
                    ukon_word = "úkonů"
                    provedeny_word = "provedených"
                unique_names = sorted(set(names))
                cost_clauses.append(
                    f"paušální náhradou za {n} {ukon_word} {provedeny_word} "
                    f"{winning_party['instrumental']} osobně před převzetím "
                    f"zastoupení po {f(sazba)} dle § 151 odst. 3 občanského "
                    f"soudního řádu a vyhlášky č. 254/2015 Sb. "
                    f"({', '.join(unique_names)})"
                )

        for (fee, paragraph), act_list in sorted(
            acts_by_fee_and_paragraph.items(), key=lambda item: item[0], reverse=True
        ):
            num_acts = len(act_list)
            ukon_word = "úkonu" if num_acts == 1 else "úkonů"
            act_names = sorted(list(set(act_list)))
            
            if not vyhlaska_defined:
                vyhlaska_text = "vyhlášky č. 177/1996 Sb. (dále jen „vyhláška“)"
                vyhlaska_defined = True
            else:
                vyhlaska_text = "vyhlášky"

            cost_clauses.append(
                f"odměnou advokáta dle {paragraph} {vyhlaska_text} v rozsahu {num_acts} {ukon_word} po {f(fee)} ({', '.join(act_names)})"
            )

        if cost_clauses:
            intro_phrase = f"Účelně vynaložené náklady jsou u {'zcela' if is_full_success or r.get('defendant_won') else 'převážně'} úspěšného {winning_party['genitive']} představovány {cost_clauses.pop(0)}."
            justification_sentences.append(intro_phrase)

            connectors = ["Dále", "Vedle toho", "Rovněž"]
            for i, clause in enumerate(cost_clauses):
                justification_sentences.append(
                    f"{connectors[i % len(connectors)]} {clause}."
                )

            travel_acts = [act for act in performed_acts if act.get("travel")]
            # V13.4.28e+: rozdělit travel_acts na AUTO (= mají amortizaci/palivo
            # v odůvodnění) a VLAK (= jen jízdné, NZČ). Vlakové úkony jdou do
            # other_expenses sentence, NE do auto-detail clause s amortizací.
            auto_travel_acts = [a for a in travel_acts
                                 if a.get("travel", {}).get("mode") != "vlak"]
            vlak_travel_acts = [a for a in travel_acts
                                 if a.get("travel", {}).get("mode") == "vlak"]
            if r["total_travel_expense"] > 0 or r["total_time_loss_comp"] > 0:
                all_travel_details = []
                grouped_travel = {}
                for act in auto_travel_acts:  # ← jen auto, ne vlak
                    travel = act["travel"]
                    rates = self.get_rates_for_date(act["date"])
                    breakdown = self.calculate_travel_cost_breakdown(travel, act["date"])
                    if breakdown and rates:
                        # V13.4.28e+ #19: zahrnout fuel_price_source do klíče —
                        # úkony s doloženou cenou se neslučují s vyhláškovými.
                        key = (
                            travel.get("city_name", "[neuvedeno]"),
                            int(breakdown["total_dist"]),
                            travel["consumption"],
                            travel["fuel_type"],
                            breakdown["fuel_price"],
                            breakdown["amort_rate"],
                            rates["cislo_vyhlasky"],
                            breakdown.get("fuel_price_source", "vyhlaska"),
                        )
                        if key not in grouped_travel:
                            grouped_travel[key] = []
                        grouped_travel[key].append(act["date"])

                travel_details_parts = []
                for (
                    city,
                    dist,
                    consum,
                    fuel_type,
                    fuel_price,
                    amort_rate,
                    vyhlaska,
                    fuel_src,
                ), dates in grouped_travel.items():
                    route = f"{city}-Pardubice a zpět"
                    # V13.4.28e+ #19: zdroj ceny paliva — vyhláška / doložená účtenka
                    if fuel_src == "manual":
                        fuel_src_text = "dle doloženého dokladu o nákupu"
                    else:
                        fuel_src_text = f"dle vyhlášky č. {vyhlaska}"
                    if len(dates) > 1:
                        dates_str = ", ".join([format_date_short(d) for d in sorted(dates)])
                        travel_details_parts.append(
                            f"trasa {route} ve dnech {dates_str}, délka trasy vždy {dist} km, "
                            f"náhrada za opotřebení vždy {f_num(amort_rate)} Kč za km, "
                            f"doložená spotřeba automobilu vždy {str(consum).replace('.',',')} l/100 km, "
                            f"cena pohonných hmot ({fuel_type}) vždy {f(fuel_price, with_unit=True)} za litr {fuel_src_text}"
                        )
                    else:
                        travel_details_parts.append(
                            f"trasa {route} dne {format_date_short(dates[0])}, délka trasy {dist} km, "
                            f"náhrada za opotřebení {f_num(amort_rate)} Kč za km, "
                            f"doložená spotřeba automobilu {str(consum).replace('.',',')} l/100 km, "
                            f"cena pohonných hmot ({fuel_type}) {f(fuel_price, with_unit=True)} za litr {fuel_src_text}"
                        )

            time_loss_parts = []
            if r["total_time_loss_comp"] > 0 and travel_acts:
                time_loss_by_rate = {}
                for act in travel_acts:
                    rates = self.get_rates_for_date(act["date"])
                    rate_nzc = rates["ztrata_casu_sazba"]
                    half_hours = math.ceil(
                        (act.get("travel", {}).get("time_min", 0) * 2) / 30
                    )
                    time_loss_by_rate[rate_nzc] = (
                        time_loss_by_rate.get(rate_nzc, 0) + half_hours
                    )

                for rate, total_half_hours in time_loss_by_rate.items():
                    vyhlaska_ref = "vyhlášky" if vyhlaska_defined else "vyhlášky č. 177/1996 Sb."
                    # V13.4.28e+: Pavlův styl — vnitřek závorky bez opakování
                    # úvodního slovesa „náhrada za ztrátu času na cestě".
                    # To se přesune do hlavní klauzule (= vnější tvar).
                    time_loss_parts.append(
                        f"podle § 14 odst. 3 {vyhlaska_ref} v rozsahu "
                        f"{total_half_hours} započatých půlhodin po {f(rate)}"
                    )

            # V13.4.28e+: All-vlak detekce. Pavlův vzor textu (= Word
            # rozsudek po manuální úpravě):
            #   „K nákladům náleží i náhrada za prokázané hotové výdaje
            #    v celkové výši 504 Kč (jízdné) a náhrada za ztrátu času
            #    na cestě ve výši 1 200 Kč (podle § 14 odst. 3 vyhlášky
            #    v rozsahu 8 započatých půlhodin po 150 Kč)."
            # → jízdné + NZČ spojené v JEDNÉ větě, bez slov o amortizaci
            # / palivu / vzdálenosti / autu.
            is_all_vlak = bool(vlak_travel_acts) and not auto_travel_acts
            include_other_in_combined = (is_all_vlak
                and r.get("total_other_expenses", 0) > 0)

            combined_details = []

            if include_other_in_combined:
                # All-vlak: jízdné jde JAKO PRVNÍ klauzule (Pavlův styl).
                # Pokud je jízdné jediný hotový výdaj, v závorce jen
                # „(jízdné)" — částka je už v hlavní výši. Pokud i parkovné,
                # rozepsat „(jízdné X Kč, parkovné Y Kč)".
                j = r.get("total_jizdne", 0.0)
                p = r.get("total_parkovne", 0.0)
                if j > 0 and p == 0:
                    detail_oth = " (jízdné)"
                elif j == 0 and p > 0:
                    detail_oth = " (parkovné)"
                else:
                    parts_oth = []
                    if j > 0: parts_oth.append(f"jízdné {f(j)}")
                    if p > 0: parts_oth.append(f"parkovné {f(p)}")
                    detail_oth = f" ({', '.join(parts_oth)})" if parts_oth else ""
                combined_details.append(
                    f"náhrada za prokázané hotové výdaje v celkové výši "
                    f"{f(r['total_other_expenses'])}{detail_oth}"
                )

            if r["total_travel_expense"] > 0:
                travel_clause = f"cestovné ve výši {f(r['total_travel_expense'])} ({'; '.join(travel_details_parts)})"
                combined_details.append(travel_clause)

            if r["total_time_loss_comp"] > 0:
                # V13.4.28e+: Pavlův styl — „náhrada za ztrátu času NA CESTĚ
                # ve výši X Kč (podle § 14 odst. 3 ...)"
                time_loss_clause = (f"náhrada za ztrátu času na cestě "
                                     f"ve výši {f(r['total_time_loss_comp'])} "
                                     f"({' a '.join(time_loss_parts)})")
                combined_details.append(time_loss_clause)

            justification_sentences.append(
                f"K nákladům náleží i {' a '.join(combined_details)}."
            )

        # Separate „hotové výdaje" věta — JEN pokud nebyla integrována výše
        # (= mix scénář, nebo jízdné/parkovné u auta).
        if (r.get("total_other_expenses", 0) > 0
                and not (vlak_travel_acts and not auto_travel_acts)):
            # V13.4.28e+: rozdělené jízdné × parkovné v textu odůvodnění,
            # aby Pavel viděl breakdown (předtím jen sumu „jízdné a parkovné")
            j = r.get("total_jizdne", 0.0)
            p = r.get("total_parkovne", 0.0)
            parts = []
            if j > 0:
                parts.append(f"jízdné {f(j)}")
            if p > 0:
                parts.append(f"parkovné {f(p)}")
            if parts:
                detail_str = f" ({', '.join(parts)})"
            else:
                detail_str = ""
            justification_sentences.append(
                f"{winning_party['dative'].capitalize()} náleží i náhrada "
                f"za prokázané hotové výdaje v celkové výši "
                f"{f(r['total_other_expenses'])}{detail_str}."
            )

        final_bits = []
        if r["total_overhead"] > 0 and performed_acts:
            overhead_counts = {}
            for act in performed_acts:
                # V13.4.28e+: úkony před převzetím zastoupení nemají režijní
                # paušál (§ 13 odst. 4 vyhlášky 177/1996 Sb. = advokátní benefit).
                if is_unrep_global or act.get("before_representation"):
                    continue
                rates = self.get_rates_for_date(act["date"])
                act_base_name = act["name"].split(" (")[0]
                if r["proc_type"] == "form" and act_base_name in self.FORMULARY_ACTS:
                    rate = rates.get("pausal_formular", 100)
                else:
                    rate = rates.get("pausal_normal", 300)
                overhead_counts[rate] = overhead_counts.get(rate, 0) + 1

            breakdown_parts = []
            for rate, count in sorted(overhead_counts.items()):
                breakdown_parts.append(f"{count}x {rate} Kč")

            breakdown_str = (
                f" ({' a '.join(breakdown_parts)})" if breakdown_parts else ""
            )
            
            vyhlaska_ref = "vyhlášky" if vyhlaska_defined else "vyhlášky č. 177/1996 Sb."
            
            final_bits.append(
                f"paušální náhrada hotových výdajů dle § 13 odst. 4 {vyhlaska_ref} za výše uvedené úkony v celkové výši {f(r['total_overhead'])}{breakdown_str}"
            )

        if r["total_vat"] > 0:
            final_bits.append(
                "jako plátci daně z přidané hodnoty dle § 137 odst. 3 písm. a) občanského soudního řádu i náhrada DPH z odměny a náhrad"
            )

        if final_bits:
            justification_sentences.append(
                f"{winning_party['dative'].capitalize()} náleží i {' a '.join(final_bits)}."
            )

        if not is_full_success and not r.get("defendant_won", False):
            plaintiff_pct_str = f"{r['plaintiff_success_pct']:.2f} %".replace(".", ",")
            net_pct_str = f"{r['net_success_pct']:.2f} %".replace(".", ",")
            justification_sentences.append(
                f"Vzhledem k úspěchu {winning_party['genitive']} ve výši {plaintiff_pct_str} má tento účastník "
                f"právo na poměrnou část nákladů odpovídající jeho čistému úspěchu {net_pct_str} (odečtení míry neúspěchu od úspěchu), "
                f"tedy na částku {claimable_amount_str}."
            )
        
        if r.get("accessory_failure", False):
            justification_sentences.append(
                "Při stanovování míry úspěchu přihlížel soud s ohledem na výše uvedené skutečnosti vztahující se k posouzení samotného nároku i k příslušenství – viz nález Ústavního soudu sp. zn. I. ÚS 2717/08 ze dne 30. 8. 2010 a nález Ústavního soudu sp. zn. II. ÚS 3070/14 ze dne 17. 1. 2017."
            )

        # V13.4.28e+: doměření SOP — pokud Pavel zaškrtl „placeno + doměřit",
        # k odůvodnění se přidá typový odstavec o doměření a poučení o
        # vymáhání celním úřadem. Pavel pak v rozsudku nemusí lovit text
        # z modulu SOP.
        domer = float(r.get("court_fee_domer", 0) or 0)
        if r.get("sop_volba") == "domer" and domer > 0:
            justification_sentences.append(
                f"V souladu s položkou 2 sazebníku soudních poplatků "
                f"(příloha zákona č. 549/1991 Sb., o soudních poplatcích) "
                f"soud doměřil žalobci soudní poplatek ve výši {f(domer)}, "
                f"neboť ve věci nebyl vydán elektronický platební rozkaz."
            )

        justification_text = " ".join(justification_sentences)
        full_justification = f"ODŮVODNĚNÍ\n{'-'*35}\n{justification_text}"

        # V13.4.28e+: pokud doměření, připojit za odůvodnění samostatný
        # výrok o doplacení (s VS + číslem účtu) + poučení o celním úřadu.
        if r.get("sop_volba") == "domer" and domer > 0:
            ucet = r.get("domer_ucet") or "3703-625561/0710"
            vs   = r.get("domer_vs")   or "—"

            extra_outputs = []
            extra_outputs.append("\n\nDODATEČNÝ VÝROK (k doměření SOP):")
            extra_outputs.append("-" * 35)
            extra_outputs.append(
                f"Žalobci se ukládá, aby doplatil do 15 dnů od právní moci "
                f"tohoto výroku České republice na účet Okresního soudu "
                f"v Pardubicích číslo {ucet} pod variabilním symbolem "
                f"{vs} soudní poplatek v částce {f(domer)}."
            )
            extra_outputs.append("\nDODATEČNÉ POUČENÍ (k doměření SOP):")
            extra_outputs.append("-" * 35)
            extra_outputs.append(
                "Nesplní-li povinný dobrovolně, co mu ukládá vykonatelné "
                "rozhodnutí, může oprávněný podat návrh na soudní výkon "
                "rozhodnutí."
            )
            extra_outputs.append(
                "Pokud nebude peněžité plnění (soudní poplatek) uhrazeno "
                "do 30 dnů po marném uplynutí lhůty jeho splatnosti, předá "
                "soud pohledávku k vymáhání místně příslušnému celnímu úřadu."
            )
            full_justification = full_justification + "\n" + "\n".join(extra_outputs)

        return f"{verdict_proposal}\n\n{full_justification}"

    def generate_calculation_summary(self, r, performed_acts):
        f = self.format_currency
        text = "PODROBNÝ ROZPIS VÝPOČTU\n" + "=" * 40 + "\n\n"
        plaintiff_pct_str = f"{r.get('plaintiff_success_pct', 0):.2f} %".replace(
            ".", ","
        )
        net_pct_str = f"{r.get('net_success_pct', 0):.2f} %".replace(".", ",")

        text += (
            "1. VSTUPY A ÚSPĚCH\n"
            + f"   - Tarifní hodnota / Žalovaná částka: {f(r['tariff_value'])}\n"
        )
        if r.get("defendant_won", False):
            text += "   - Výsledek: Žalovaný vyhrál\n\n"
        else:
            text += f"   - Přiznaná částka: {f(r['awarded_amount'])}\n"
            text += f"   - Úspěch žalobce: {plaintiff_pct_str}\n"
            text += f"   - Čistý úspěch (rozdíl): {net_pct_str}\n\n"

        text += "2. VÝPOČET NÁKLADŮ STRANY\n"
        if r.get("unrepresented_party", False):
            text += "   A) Paušální náhrada (nezastoupený účastník):\n"
            for act in performed_acts:
                text += f"     - Úkon '{act['name']}' ({act['date'].strftime('%d.%m.%Y')}): {f(300)}\n"
            text += f"     --- Celkem paušál za úkony: {f(r['total_fee_base'])}\n"
        else:
            text += "   A) Odměna advokáta:\n"
            for act in performed_acts:
                if act.get("manual_fee") is not None:
                    fee = act["manual_fee"]
                    text += f"     - Úkon '{act['name']}' ({act['date'].strftime('%d.%m.%Y')}) [MANUÁLNĚ UPRAVENO]: {f(fee)}\n"
                elif r.get("global_manual_fee") is not None:
                    fee = r["global_manual_fee"]
                    text += f"     - Úkon '{act['name']}' ({act['date'].strftime('%d.%m.%Y')}) [GLOBÁLNÍ RUČNÍ SAZBA]: {f(fee)}\n"
                else:
                    act_tariff_value = act.get("tariff_value", r["tariff_value"])
                    fee = self.get_fee_per_act(
                        act["name"], act_tariff_value, act["date"], r["proc_type"]
                    )
                    text += f"     - Úkon '{act['name']}' ({act['date'].strftime('%d.%m.%Y')}) [tarif {f(act_tariff_value)}]: {f(fee)}\n"

            if r["modification"] != "none":
                mod_factor = (
                    0.5
                    if r["modification"] == "half"
                    else (3 if r["modification"] == "treble" else 1)
                )
                base_fee = r["total_fee_base"] / mod_factor
                text += (
                    f"     --- Celkem odměna (před modifikací): {f(base_fee)}\n"
                    + f"     --- Po modifikaci ({r['modification']}): {f(r['total_fee_base'])}\n"
                )
            else:
                text += f"     --- Celkem odměna: {f(r['total_fee_base'])}\n"
            text += (
                "\n   B) Paušální náhrady (režie):\n"
                + f"     - Počet úkonů: {len(performed_acts)}\n"
                + f"     --- Celkem paušál: {f(r['total_overhead'])}\n"
            )

        if (
            r["total_travel_expense"] > 0
            or r["total_time_loss_comp"] > 0
            or r["total_other_expenses"] > 0
        ):
            text += "\n   C) Cestovní náhrady a další výdaje:\n"
            if r["total_travel_expense"] > 0:
                text += f"     - Cestovné (palivo + amortizace): {f(r['total_travel_expense'])}\n"
            if r["total_time_loss_comp"] > 0:
                text += (
                    f"     - Náhrada za ztrátu času: {f(r['total_time_loss_comp'])}\n"
                )
            if r["total_other_expenses"] > 0:
                # V13.4.28e+: rozdělit na jízdné × parkovné
                j = r.get("total_jizdne", 0.0)
                p = r.get("total_parkovne", 0.0)
                if j > 0:
                    text += f"     - Jízdné: {f(j)}\n"
                if p > 0:
                    text += f"     - Parkovné: {f(p)}\n"
                # Fallback pokud jen suma (starý uložený stav)
                if j == 0 and p == 0:
                    text += f"     - Ostatní (jízdné, parkovné): {f(r['total_other_expenses'])}\n"

        if not r.get("unrepresented_party", False):
            text += (
                "\n   D) Mezisoučet a DPH:\n"
                + f"     - Mezisoučet (pro DPH): {f(r['subtotal_advocate'])}\n"
                + f"     - DPH: {f(r['total_vat'])}\n"
            )

        text += "\n   E) Soudní poplatek:\n"
        if r.get("refund_sop", False):
            text += (
                f"     - Původně zaplacený SOP: {f(r['original_court_fee'])}\n"
                + f"     - Uplatněná část SOP (po vrácení): {f(r['court_fee_paid'])}\n"
            )
        else:
            text += f"     - Zaplacený SOP: {f(r['court_fee_paid'])}\n"
        text += (
            "\n   F) CELKOVÉ NÁKLADY STRANY:\n" + f"     - {f(r['grand_total'])}\n\n"
        )
        text += "3. FINÁLNÍ NÁROK\n"
        if r.get("defendant_won", False):
            text += f"   - Nárok na náhradu (100 % nákladů žalovaného):\n     {f(r['claimable_amount'])}\n"
        else:
            text += f"   - Nárok na náhradu ({net_pct_str} z celkových nákladů):\n     {f(r['claimable_amount'])}\n"
        return text

    def generate_excel_report(self, filepath, r, performed_acts):
        if not HAS_OPENPYXL:
            return False, "Knihovna openpyxl není nainstalována."

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Vyúčtování"

        # Styly
        bold_font = Font(bold=True)
        header_font = Font(bold=True, size=12)
        currency_format = '#,##0.00 "Kč"'
        
        # Nastavení šířky sloupců
        ws.column_dimensions['A'].width = 60
        ws.column_dimensions['B'].width = 20

        row_idx = 1

        def write_line(label, value=None, is_header=False, is_bold=False, is_currency=False):
            nonlocal row_idx
            cell_a = ws.cell(row=row_idx, column=1, value=label)
            if is_header:
                cell_a.font = header_font
            if is_bold:
                cell_a.font = bold_font
            
            if value is not None:
                cell_b = ws.cell(row=row_idx, column=2, value=value)
                if is_bold:
                    cell_b.font = bold_font
                if is_currency:
                    cell_b.number_format = currency_format
                cell_b.alignment = Alignment(horizontal='right')
            
            row_idx += 1

        # 1. Hlavička
        write_line("PODROBNÝ ROZPIS VÝPOČTU NÁKLADŮ ŘÍZENÍ", is_header=True)
        row_idx += 1

        # 2. Vstupy
        write_line("1. VSTUPY A ÚSPĚCH", is_bold=True)
        write_line(f"Tarifní hodnota: {self.format_currency(r['tariff_value'])}")
        write_line(f"Přiznaná částka: {self.format_currency(r['awarded_amount'])}")
        write_line(f"Úspěch ve věci: {r['plaintiff_success_pct']:.2f} %")
        row_idx += 1

        # 3. Odměna
        write_line("2. VÝPOČET NÁKLADŮ", is_bold=True)
        write_line("A) Odměna advokáta (mimosmluvní odměna)", is_bold=True)
        
        for act in performed_acts:
            date_str = act['date'].strftime('%d.%m.%Y')
            if act.get("manual_fee") is not None:
                fee = act["manual_fee"]
                note = "[MANUÁLNĚ]"
            elif r.get("global_manual_fee") is not None:
                fee = r["global_manual_fee"]
                note = "[GLOBÁLNÍ RUČNÍ]"
            else:
                act_tariff = act.get("tariff_value", r["tariff_value"])
                fee = self.get_fee_per_act(act["name"], act_tariff, act["date"], r["proc_type"])
                note = ""
            
            label = f"{date_str} - {act['name']} {note}"
            write_line(label, fee, is_currency=True)
        
        if r["modification"] != "none":
             write_line(f"Modifikace ({r['modification']})", r['total_fee_base'], is_bold=True, is_currency=True)
        else:
             write_line("Celkem odměna", r['total_fee_base'], is_bold=True, is_currency=True)
        row_idx += 1

        # 4. Režijní paušály
        write_line("B) Režijní paušály (§ 13 odst. 4 AT)", is_bold=True)
        for act in performed_acts:
            rates = self.get_rates_for_date(act["date"])
            act_base_name = act["name"].split(" (")[0]
            if r["proc_type"] == "form" and act_base_name in self.FORMULARY_ACTS:
                rate = rates.get("pausal_formular", 100)
            else:
                rate = rates.get("pausal_normal", 300)
            
            label = f"Paušál k úkonu: {act['name']}"
            write_line(label, rate, is_currency=True)
        
        write_line("Celkem režijní paušály", r['total_overhead'], is_bold=True, is_currency=True)
        row_idx += 1

        # 5. Cestovné - DETAILNÍ VÝPIS
        if r['total_travel_expense'] > 0 or r['total_time_loss_comp'] > 0:
            write_line("C) Cestovní náhrady a ztráta času", is_bold=True)
            
            for act in performed_acts:
                if not act.get("travel"):
                    continue
                
                travel = act["travel"]
                breakdown = self.calculate_travel_cost_breakdown(travel, act["date"])
                nzc = self.calculate_time_loss_comp(travel, act["date"])
                
                if breakdown:
                    # Nadpis pro konkrétní cestu
                    write_line(f"Cesta: {act['name']} ({act['date'].strftime('%d.%m.%Y')})", is_bold=True)

                    if breakdown.get("mode") == "vlak":
                        # V13.4.28e+: vlak — bez amortizace + paliva
                        write_line(f"  Zástupce cestoval vlakem")
                        if travel.get("city_name"):
                            write_line(f"  Trasa: {travel['city_name']} <-> Pardubice")
                        if travel.get("jizdne", 0) > 0:
                            write_line("  -> Jízdné (vlak)", travel['jizdne'], is_currency=True)
                        if nzc > 0:
                            half_hours = math.ceil((travel.get("time_min", 0) * 2) / 30)
                            rates = self.get_rates_for_date(act["date"])
                            rate_nzc = rates["ztrata_casu_sazba"]
                            write_line(f"  -> Náhrada za promeškaný čas ({half_hours} půlhodin x {rate_nzc} Kč)",
                                        nzc, is_currency=True)
                        if travel.get("parkovne", 0) > 0:
                            write_line("  -> Parkovné u nádraží", travel['parkovne'], is_currency=True)
                    else:
                        # Auto mode (= stávající chování)
                        write_line(f"  Trasa: {travel['city_name']} <-> Pardubice")
                        write_line(f"  Vzdálenost: {travel['distance_km']} km x 2 = {breakdown['total_dist']} km")
                        write_line(f"  Spotřeba: {travel['consumption']} l/100km ({travel['fuel_type']})")
                        write_line(f"  Cena paliva (vyhláška): {breakdown['fuel_price']:.2f} Kč/l")
                        write_line(f"  Sazba amortizace: {breakdown['amort_rate']:.2f} Kč/km")

                        # Výpočet řádek po řádku do pravého sloupce
                        write_line("  -> Náhrada za palivo", breakdown['fuel_cost'], is_currency=True)
                        write_line("  -> Náhrada za amortizaci", breakdown['amort_cost'], is_currency=True)

                        if nzc > 0:
                            half_hours = math.ceil((travel.get("time_min", 0) * 2) / 30)
                            rates = self.get_rates_for_date(act["date"])
                            rate_nzc = rates["ztrata_casu_sazba"]
                            write_line(f"  -> Ztráta času ({half_hours} půlhodin x {rate_nzc} Kč)", nzc, is_currency=True)

                        if travel.get("jizdne", 0) > 0:
                            write_line("  -> Jízdné", travel['jizdne'], is_currency=True)
                        if travel.get("parkovne", 0) > 0:
                            write_line("  -> Parkovné", travel['parkovne'], is_currency=True)
                    
                    row_idx += 1 # Mezera mezi cestami

            # Součty sekce C
            write_line("Celkem cestovné (palivo + amortizace)", r['total_travel_expense'], is_bold=True, is_currency=True)
            write_line("Celkem náhrada za ztrátu času", r['total_time_loss_comp'], is_bold=True, is_currency=True)
            write_line("Celkem ostatní (jízdné, parkovné)", r['total_other_expenses'], is_bold=True, is_currency=True)
            row_idx += 1

        # 6. DPH a Mezisoučet
        write_line("D) Rekapitulace a DPH", is_bold=True)
        write_line("Mezisoučet pro DPH", r['subtotal_advocate'], is_currency=True)
        if r['total_vat'] > 0:
            write_line(f"DPH {int(self.VAT_RATE*100)}%", r['total_vat'], is_currency=True)
        else:
            write_line("DPH", 0, is_currency=True)
        row_idx += 1

        # 7. Soudní poplatek
        write_line("E) Soudní poplatek", is_bold=True)
        write_line("Zaplacený SOP", r['court_fee_paid'], is_currency=True)
        row_idx += 1

        # 8. Celkem
        write_line("CELKOVÉ NÁKLADY STRANY", r['grand_total'], is_bold=True, is_currency=True)
        
        # Zvýraznění celkové částky barvou
        total_cell = ws.cell(row=row_idx-1, column=2)
        total_cell.fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
        total_cell.border = Border(bottom=Side(style='double'))

        row_idx += 1
        write_line("3. FINÁLNÍ NÁROK K PŘIZNÁNÍ", is_bold=True)
        write_line(f"Nárok ({r['net_success_pct']:.2f} %)", r['claimable_amount'], is_bold=True, is_currency=True)
        
        final_cell = ws.cell(row=row_idx-1, column=2)
        final_cell.font = Font(bold=True, size=12, color="FF0000")

        try:
            wb.save(filepath)
            return True, "OK"
        except Exception as e:
            return False, str(e)
# === BLOK CALCULATION_ENGINE END ===
