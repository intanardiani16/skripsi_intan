-- =====================================================================
-- Star Schema Data Mart EDC MTI Bank X  (database: HISTORY_MERCHANT)
-- Dipisahkan per batch dengan GO. Aman dijalankan berulang kali.
-- =====================================================================

-- ---------- STAGING / RAW (hasil upload Excel, tidak diubah) ----------
IF OBJECT_ID('dbo.RAW_HISTORY_MERCHANT','U') IS NULL
CREATE TABLE dbo.RAW_HISTORY_MERCHANT (
    RSON_CTNTS_INTN NVARCHAR(255), RSON_CTNTS_RSPN NVARCHAR(255), RSON_CTNTS_ISSUR NVARCHAR(255),
    ACQ_MB_MID NVARCHAR(50), merchant_name_alz NVARCHAR(255), MID NVARCHAR(50), TID NVARCHAR(50),
    trx_date NVARCHAR(50), trx_time NVARCHAR(20), merchant_type NVARCHAR(255),
    regional_performance NVARCHAR(255), card_type NVARCHAR(50), status_trx NVARCHAR(50),
    ACQ_MB_NO NVARCHAR(50), CARD_NO NVARCHAR(50), sales_volume NVARCHAR(50), respone_code NVARCHAR(10),
    trx_type NVARCHAR(100), ONOFF NVARCHAR(20), USER_DECLINE NVARCHAR(100),
    OFFCL_MER_NM NVARCHAR(255), ISSUER_NAME NVARCHAR(255)
);
GO
-- ---------- DIMENSI ----------
IF OBJECT_ID('dbo.DIM_MERCHANT','U') IS NULL
CREATE TABLE dbo.DIM_MERCHANT (
    merchant_key INT PRIMARY KEY,
    MID NVARCHAR(50) NOT NULL,
    merchant_name_alz NVARCHAR(255),
    merchant_type NVARCHAR(255),
    regional_performance NVARCHAR(255)
);
GO
IF OBJECT_ID('dbo.DIM_WAKTU','U') IS NULL
CREATE TABLE dbo.DIM_WAKTU (
    date_key INT PRIMARY KEY,          -- YYYYMMDD
    tanggal DATE NOT NULL,
    tahun INT NOT NULL,
    bulan NVARCHAR(20) NOT NULL,
    bulan_no INT NOT NULL,
    nama_hari NVARCHAR(20) NOT NULL    -- dipakai Same-Day Merchant Comparison
);
GO
IF OBJECT_ID('dbo.DIM_KARTU','U') IS NULL
CREATE TABLE dbo.DIM_KARTU (card_key INT PRIMARY KEY, card_type NVARCHAR(50) NOT NULL);
GO
IF OBJECT_ID('dbo.DIM_JENIS_TRANSAKSI','U') IS NULL
CREATE TABLE dbo.DIM_JENIS_TRANSAKSI (trx_type_key INT PRIMARY KEY, trx_type NVARCHAR(100) NOT NULL);
GO
-- ---------- FAKTA ----------
IF OBJECT_ID('dbo.FACT_TRANSAKSI_EDC','U') IS NULL
CREATE TABLE dbo.FACT_TRANSAKSI_EDC (
    transaction_key INT PRIMARY KEY,
    merchant_key INT NOT NULL REFERENCES dbo.DIM_MERCHANT(merchant_key),
    date_key INT NOT NULL REFERENCES dbo.DIM_WAKTU(date_key),
    card_key INT NOT NULL REFERENCES dbo.DIM_KARTU(card_key),
    trx_type_key INT NOT NULL REFERENCES dbo.DIM_JENIS_TRANSAKSI(trx_type_key),
    sales_volume DECIMAL(18,2) NOT NULL,
    status_trx NVARCHAR(20) NOT NULL,   -- 'Approved' / 'Declined'
    trx_time CHAR(8) NULL               -- HH:MM:SS (untuk Latest Transaction)
);
GO
CREATE OR ALTER VIEW dbo.VW_TRANSAKSI AS
SELECT f.transaction_key, f.trx_time, f.sales_volume, f.status_trx,
       m.MID, m.merchant_name_alz, m.merchant_type, m.regional_performance,
       w.date_key, w.tanggal, w.tahun, w.bulan, w.bulan_no, w.nama_hari,
       k.card_type, j.trx_type
FROM dbo.FACT_TRANSAKSI_EDC f
JOIN dbo.DIM_MERCHANT m ON m.merchant_key = f.merchant_key
JOIN dbo.DIM_WAKTU w ON w.date_key = f.date_key
JOIN dbo.DIM_KARTU k ON k.card_key = f.card_key
JOIN dbo.DIM_JENIS_TRANSAKSI j ON j.trx_type_key = f.trx_type_key;
GO
