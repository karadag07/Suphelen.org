# Suphelen.org - Şüpheli İçerik Analiz ve Doğrulama Sistemi

Suphelen.org, kullanıcıların şüpheli gördüğü içerikleri analiz ederek doğruluk kontrolü yapan ve güvenilir kaynaklarla karşılaştıran bir sistemdir. Proje, yanlış bilgi (dezenformasyon) problemini azaltmayı hedefler.

## Proje Amacı

Günümüzde internet üzerinde hızla yayılan yanlış veya manipüle edilmiş içerikler, toplum üzerinde ciddi etkilere yol açmaktadır.
Bu proje:

* Kullanıcıdan alınan içerikleri analiz eder
* Güvenilir kaynaklarla karşılaştırır
* İçeriğin doğruluğu hakkında geri bildirim sağlar

Amaç, kullanıcıların doğru bilgiye daha hızlı ve güvenilir şekilde ulaşmasını sağlamaktır.

---

## Sistem Nasıl Çalışır?

1. Kullanıcı sisteme bir içerik girer (haber, metin veya bağlantı)
2. Sistem bu içeriği analiz eder
3. İçerik güvenilir veri kaynakları ile karşılaştırılır
4. Sonuç kullanıcıya sunulur

---

## Proje Mimarisi

```text
Client (Frontend / Kullanıcı)
        ↓
Backend API (Spring Boot / Servis)
        ↓
Veri Kaynakları / Analiz Katmanı
```

---

## Kullanılan Teknolojiler

### Backend

* Java
* Spring Boot
* REST API
* JSON veri işleme

### Frontend

* Web tabanlı kullanıcı arayüzü

### Diğer

* API tabanlı veri analizi
* Veri karşılaştırma ve doğrulama mantığı

---

## Öne Çıkan Özellikler

* Şüpheli içerik analizi
* Kullanıcı odaklı basit arayüz
* Doğrulama ve karşılaştırma sistemi
* Gerçek dünya problemini hedefleyen yapı
* Modüler ve geliştirilebilir mimari

---

## Kullanım Senaryosu

1. Kullanıcı şüpheli bir haber ile karşılaşır
2. Haberi sisteme girer
3. Sistem analiz yapar
4. Kullanıcıya içeriğin güvenilirliği hakkında bilgi verilir

---

## Hedef

Bu sistemin amacı:

* Dezenformasyonu azaltmak
* Kullanıcıları bilinçlendirmek
* Bilgi doğrulama süreçlerini hızlandırmak

