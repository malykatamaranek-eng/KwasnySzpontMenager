/*
 * KwasnySzpontMenager – model domenowy marketplace
 *
 * Plik definiuje typy współdzielone pomiędzy aplikacjami frontendowymi
 * a mikroserwisami backendowymi. Nazewnictwo odzwierciedla specyfikę
 * polskiego marketplace (Przelewy24, kody pocztowe, NIP itp.).
 */

// ── Role uczestników platformy ──────────────────────────────────

export type RolaUczestnika = "kupujacy" | "sprzedawca" | "administrator" | "obsluga_klienta";

// ── Konto użytkownika ───────────────────────────────────────────

export interface KontoUzytkownika {
  idKonta: string;
  adresEmail: string;
  nazwaPrezentacyjna: string;
  rola: RolaUczestnika;
  urlAvatara?: string;
  zweryfikowanoData?: string;
  nip?: string;                    // numer NIP – wymagany dla sprzedawców
  utworzonoData: string;
  zmodyfikowanoData: string;
}

// ── Katalog produktów ───────────────────────────────────────────

export interface WariantProduktu {
  idWariantu: string;
  etykieta: string;               // np. "Rozmiar M", "Kolor czerwony"
  dopłata: number;                // grosze – dopłata do ceny bazowej
  stanMagazynowy: number;
}

export interface WpisProduktu {
  idWpisu: string;
  idSprzedawcy: string;
  tytul: string;
  slug: string;
  opis: string;
  cenaBazowaGrosze: number;       // cena w groszach (1 zł = 100 groszy)
  kodWaluty: string;              // np. "PLN", "EUR"
  warianty: WariantProduktu[];
  tagi: string[];
  urlZdjec: string[];
  czyOpublikowany: boolean;
  dataPublikacji?: string;
  utworzonoData: string;
  zmodyfikowanoData: string;
}

// ── Koszyk ──────────────────────────────────────────────────────

export interface PozycjaKoszyka {
  idWpisu: string;
  idWariantu?: string;
  ilosc: number;
  cenaJednostkowaGrosze: number;
}

export interface KoszykZakupowy {
  idKoszyka: string;
  idKupujacego: string;
  pozycje: PozycjaKoszyka[];
  ostatniaModyfikacja: string;
}

// ── Zamówienia ──────────────────────────────────────────────────

export type StatusZamowienia =
  | "oczekujace"
  | "potwierdzone"
  | "wRealizacji"
  | "wyslane"
  | "dostarczone"
  | "anulowane"
  | "zwrocone";

export interface AdresPocztowy {
  linia1: string;
  linia2?: string;
  miasto: string;
  wojewodztwo: string;
  kodPocztowy: string;            // format XX-XXX
  kodKraju: string;               // ISO 3166-1 alpha-2, np. "PL"
}

export interface ZamowienieMarketplace {
  idZamowienia: string;
  idKupujacego: string;
  idSprzedawcy: string;
  pozycje: PozycjaKoszyka[];
  kwotaCalkowitaGrosze: number;
  kodWaluty: string;
  status: StatusZamowienia;
  adresDostawy: AdresPocztowy;
  numerSledzenia?: string;
  dataZlozenia: string;
  dataAktualizacji: string;
}

// ── Płatności ───────────────────────────────────────────────────

export type MetodaPlatnosci = "karta" | "przelew_bankowy" | "blik" | "przelewy24" | "portfel_cyfrowy";

export interface RekordPlatnosci {
  idPlatnosci: string;
  idZamowienia: string;
  metoda: MetodaPlatnosci;
  kwotaPobrana: number;
  kodWaluty: string;
  referencjaDostawcy: string;     // np. identyfikator Stripe / P24
  dataUkonczenia?: string;
  przyczynaOdrzucenia?: string;
  utworzonoData: string;
}

// ── Recenzje ────────────────────────────────────────────────────

export interface RecenzjaProduktu {
  idRecenzji: string;
  idWpisu: string;
  idAutora: string;
  ocenaGwiazdki: number;          // 1–5
  naglowek: string;
  tresc: string;
  urlZdjec: string[];
  czyZweryfikowanyZakup: boolean;
  utworzonoData: string;
}

// ── Powiadomienia ───────────────────────────────────────────────

export type KanalPowiadomienia = "w_aplikacji" | "email" | "sms" | "push";

export interface PowiadomienieMarketplace {
  idPowiadomienia: string;
  idOdbiorcy: string;
  kanal: KanalPowiadomienia;
  temat: string;
  tresc: string;
  dataOdczytu?: string;
  dataWyslania: string;
}

// ── Geolokalizacja ─────────────────────────────────────────────

export interface WspolrzedneGeo {
  szerokosc: number;              // latitude
  dlugosc: number;                // longitude
}

// ── Stronicowanie ───────────────────────────────────────────────

export interface WynikStronicowany<T> {
  elementy: T[];
  calkowitaLiczba: number;
  indeksStrony: number;
  rozmiarStrony: number;
  czyJestNastepna: boolean;
}

// ── Health-check serwisu ────────────────────────────────────────

export interface RaportZdrowiaSerwisu {
  nazwaSerwisu: string;
  kondycja: "zdrowy" | "obnizony" | "niedzialajacy";
  sprawdzonoData: string;
  szczegoly?: Record<string, unknown>;
}
