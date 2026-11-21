# MarketLab PostgreSQL şemasını okumak

MarketLab, bir siparişte farklı satıcıların ürünlerini bir araya getiren bir pazaryeri projesidir. Müşteri bir ürün varyantını belirli bir satıcının ilanından satın alır. Aynı satıcı ürünü iki depoda tutuyorsa bir sipariş kalemi iki rezervasyona ve iki ayrı sevkiyata dönüşebilir. Şemadaki anahtarların ve miktar kontrollerinin çoğu bu ayrımla ilgilidir.

CS 202’nin 17 Kasım 2026 duyurusu, PostgreSQL üzerinde çalıştırıldığında tabloları ve aralarındaki ilişkileri oluşturan bir SQL dosyası istiyor. Örnek veri bu aşamada isteğe bağlı. Projenin ekip üyeleri Uygar Ege Kocakır ve Barlas Şen. [Ödev duyurusu](https://lms.ozyegin.edu.tr/mod/forum/discuss.php?d=6796#p16972) · [PostgreSQL teslim dosyası](../marketlab_postgres.sql)

## Kurulum

PostgreSQL sunucusu çalışırken, proje dizininde aşağıdaki iki komutu sırayla çalıştır. İlk komut boş bir veritabanı oluşturur. İkinci komut SQL dosyasını o veritabanında yürütür ve ilk hatada durur. pgAdmin kullanıyorsan boş bir veritabanı oluştur, o veritabanının Query Tool ekranında dosyanın tamamını aç ve çalıştır.

```sh
createdb marketlab
psql -X -v ON_ERROR_STOP=1 -d marketlab -f marketlab_postgres.sql
```

**Yeniden kurulum mevcut proje verilerini siler.** Betik, başında listelenen tabloları `DROP TABLE ... CASCADE` ile kaldırır. Bu tablolara bağımlı başka nesneler de etkilenebilir. Sonra tabloları, anahtarları, indeksleri ve tetikleyicileri tek işlem içinde oluşturur. Sondaki `COMMIT` başarılı olursa kurulum tamamlanır. İlk incelemede ve son doğrulamada PostgreSQL 18.6 kullanıldı.

Yeni ve boş bir veritabanında, varsayılan `public` şemasıyla kurulumdan sonra şu iki sorgu sırasıyla **79 tablo** ve **117 yabancı anahtar** verir. Birincil anahtar sayısı da 79’dur. Fiziksel tabloların bir bölümü varlıklar arasındaki ilişkileri temsil eder. Bu yüzden ER raporundaki 67 varlık ve 100 ilişki ile bu sayıların farklı olması beklenir.

```sql
SELECT count(*) FROM pg_tables WHERE schemaname = 'public';

SELECT contype, count(*)
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace AND contype IN ('p', 'f')
GROUP BY contype;
```

## Tabloları işlem sırasıyla okumak

| İş adımı | İlgili tablolar | Neyi temsil ediyor? |
| --- | --- | --- |
| Hesap ve adres | `accounts`, `customers`, `staff`, `couriers`, `addresses` | Ortak kimlik tek yerde durur. Alt türler kendi bilgilerini taşır. Adres bir hesaba aittir. |
| Katalog ve satış | `products`, `variants`, `listings`, `seller_organizations` | Ürün, satılabilir varyant ve satıcının o varyanta verdiği fiyat ayrı kayıtlardır. Bir satıcı aynı varyant için tek ilan açabilir. |
| Stok ve tedarik | `stock_positions`, `stock_batches`, `storage_bins`, `purchase_orders`, `goods_receipt_lines` | Stok pozisyonu satıcı, varyant ve depoyu birlikte tanımlar. Partinin rafı aynı depoda olmalı. Mal kabul satırı ilgili satın alma siparişine ait olmalı. |
| Sipariş ve ödeme | `orders`, `order_lines`, `payment_methods`, `payments`, `invoices` | Sipariş kalemi satın alınan ilanı, miktarı ve birim fiyatı saklar. Ödeme yöntemi ve fatura adresi siparişin müşterisine ait olmalı. |
| Rezervasyon ve sevkiyat | `stock_reservations`, `fulfillments`, `fulfillment_lines`, `packages`, `shipments` | Kalemin hangi depolardan karşılanacağı önce rezerve edilir. Sevkiyat satırları aynı kalemin ilgili satıcı ve depodaki rezervasyonunu tüketir. |
| İade ve ödeme hareketleri | `return_requests`, `return_lines`, `payment_transactions` | İade satırı özgün sipariş kalemine bağlanır. Para iadesinde ödeme ve iade talebi aynı siparişe ait olmalı. |

Tabloların tek tek açıklamaları ve ilişkilerin kardinaliteleri kavramsal ER raporunda yer alıyor. Tarayıcı demosu ise Python ve SQLite kullanıyor. Demoyu başlatmak veya SQLite testlerinin geçmesi PostgreSQL dosyasını çalıştırmış olmaz. [ER raporu](REPORT.md) · [Demo şeması](../schema.sql)

## Dört ER kavramının SQL karşılığı

- **Zayıf varlık.** `order_lines` içinde yalnızca `line_no = 1` bilgisi bir kalemi tanımlamaz. Anahtar `(order_id, line_no)` olduğundan iki farklı siparişin de birinci kalemi olabilir. Sipariş numarası ayrıca `orders` tablosuna yabancı anahtardır.
- **ISA ve ayrıklık.** Müşterinin, personelin ve kuryenin `role` sütunu PostgreSQL tarafından o alt türe ait sabit değerle üretilir. Örneğin bir personel kaydındaki `(account_id, 'staff')` çifti, `accounts(account_id, role)` içinde bulunmalı. Aynı hesap iki farklı role sahip olamadığı için çakışan alt tür kayıtları eşzamanlı işlemlerde de reddedilir. Her hesap için en az bir alt tür oluşturma sorumluluğu uygulamadadır.
- **Üçlü ilişki.** `stock_positions` anahtarı `(seller_id, variant_id, warehouse_id)` üçlüsüdür. Satıcı ve varyant aynı kalsa bile depo değişince ayrı bir stok pozisyonu oluşur.
- **Aggregation.** `stock_reservations` bir sipariş kalemini bu üçlü ilişkinin belirli bir kaydına bağlar. Böylece “bu kalemin iki adedi hangi satıcının hangi depodaki stoğundan ayrıldı?” sorusunun cevabı tek rezervasyon kaydında bulunur.

## Birleşik anahtarlar neden kullanılıyor?

İki kaydın ayrı ayrı var olması birbirlerine uygun olduklarını göstermez. Rezervasyonda hem geçerli bir kalem hem de geçerli bir stok pozisyonu seçilip yanlış satıcının ürünü ayrılabilirdi. `set_reservation_listing` tetikleyici fonksiyonu ilanın kimliğini sipariş kaleminden doldurur. Kalem bulunamazsa yabancı anahtar ihlalini belirten `23503` hatasıyla durur. Ardından üç yabancı anahtar aynı rezervasyonda şu bağları kurar.

1. `(order_id, line_no, listing_id)` siparişte seçilen kaleme ve ilana uyar.
2. `(listing_id, seller_id, variant_id)` o ilanın gerçek satıcısına ve varyantına uyar.
3. `(seller_id, variant_id, warehouse_id)` var olan bir stok pozisyonuna uyar.

Aynı yöntem adres, ödeme ve iadelerde de kullanılır. Örneğin bir siparişte fatura adresi olarak seçilen adresin sahibi, siparişi veren müşteri olmalıdır. Siparişte teslimat biçimi ayrıca bir `CHECK` ile seçilir. Adrese teslim ve teslim alma noktası seçeneklerinden tam biri dolu olmalıdır. Fatura adresi her iki durumda da zorunludur.

## Beş adetlik siparişin işlem boyunca durumu

Bir satıcının aynı varyantından **5 adet** sipariş edildiğini düşün. Kalem ve rezervasyonlar tek bir `BEGIN`–`COMMIT` işlemi içinde yazılır. Birinci depodan 3, ikinci depodan 2 adet ayrılır. İlk rezervasyon eklendiğinde ara toplam 3’tür. Kontrolün işlem sonuna ertelenmesi bu geçici duruma izin verir.

| Kontrol | Kabul edilen örnek | Hata veren örnek |
| --- | --- | --- |
| Rezervasyon toplamı | İki depodan 3 + 2 = 5 adet | Toplam 4 veya 6 adet ile işlemi tamamlama |
| Sevkiyat toplamı | Birinci depodan önce 2, sonra 1 adet gönderme | Aynı depodan 2 + 2 adet gönderme. Diğer deponun 2 adedi bu açığı kapatamaz. |
| İade miktarı | Bekleyen ve onaylı taleplerde aynı kalem için toplam en fazla 5 adet | İki aktif talepte toplam 6 adet. Reddedilmiş talepler bu toplama girmez. |

`check_changed_orders` değişen kaydın siparişini bulur. Bir satır başka siparişe taşınırsa her iki sipariş de kontrol edilir. `check_order_allocation` sipariş bazında yukarıdaki toplamları denetler. İlgili satırlardaki ekleme, güncelleme ve silmelerin yanı sıra sevkiyatın satıcı/depo değişikliği ve iade talebinin durum değişikliği de denetimi tetikler. Bir kural bozulduğunda `23514` hatası gelir. Rezervasyon tablosunda `TRUNCATE` kullanıldığında kalan sipariş kalemleri için kontrol yeniden sıraya alınır.

Eşzamanlı iki bağlantı aynı depodaki son birimi sevk etmeye çalışabilir. Kontrol fonksiyonu siparişin `placed_at` değerini kendisine yazar. Değer aynı kalır ama PostgreSQL yeni satır sürümü oluşturur. Böylece aynı siparişin kontrolleri sıraya girer. `READ COMMITTED` altında ikinci işlem yeni toplamı görür. `REPEATABLE READ` altında çakışan işlem `40001` serileştirme hatası alabilir ve baştan denenmesi gerekir.

## Doğrulama ve sınırlar

Sipariş miktarıyla eşleşen rezervasyon, depoda gerçekten o kadar ürün bulunduğunu tek başına göstermez. Benzer şekilde bir para iadesinin doğru siparişe bağlı olması, tutarının tahsilatı aşmadığını göstermez. Bu ayrımların örnekleri, çalıştırılan testler ve bilinen dört açık iş kuralı inceleme kaydında yer alıyor. [İnceleme ve test sonuçları](POSTGRESQL_INCELEME.md)
