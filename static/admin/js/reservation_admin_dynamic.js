/**
 * static/admin/js/reservation_admin_dynamic.js
 *
 * فیلتر دینامیک نوبت‌های زمانی بر اساس نوع مشاوره در صفحه ادمین Reservation
 */

(function ($) {
    'use strict';

    $(document).ready(function () {
        var $serviceType = $('#id_service_type');
        var $timeSlot = $('#id_time_slot');

        if (!$serviceType.length || !$timeSlot.length) {
            return;
        }

        // ذخیره تمام آپشن‌ها
        var allOptions = $timeSlot.find('option').clone();

        function filterTimeSlots() {
            var selectedServiceType = $serviceType.val();

            if (!selectedServiceType) {
                // اگر هیچ نوع مشاوره‌ای انتخاب نشده، همه رو نشون بده
                $timeSlot.html(allOptions.clone());
                return;
            }

            // فیلتر کردن آپشن‌ها
            var filteredOptions = allOptions.filter(function () {
                var $option = $(this);
                var optionText = $option.text();

                // استخراج نام نوع مشاوره از متن آپشن
                // فرمت: "نوع مشاوره - 1403/09/17 (شنبه) 09:00-09:30"
                var serviceTypeName = $('[data-service-type-id="' + selectedServiceType + '"]').text();

                // اگر آپشن خالی است (---) یا شامل نام نوع مشاوره است
                return $option.val() === '' || optionText.includes(serviceTypeName);
            });

            // آپدیت dropdown
            $timeSlot.html(filteredOptions);

            // اگر فقط یک آپشن وجود داره (علاوه بر ---) اون رو انتخاب کن
            if (filteredOptions.length === 2) {
                $timeSlot.val(filteredOptions.last().val());
            }
        }

        // رویداد تغییر نوع مشاوره
        $serviceType.on('change', filterTimeSlots);

        // اجرای فیلتر در بارگذاری اولیه
        filterTimeSlots();
    });
})(django.jQuery);