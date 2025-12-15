import uuid

from django import forms
from django.utils.safestring import mark_safe


class ModernTimePickerWidget(forms.TimeInput):
    """
    Modern scrollable time picker like phone apps
    Hour, Minute, AM/PM selection with smooth scrolling
    Beautiful green-blue gradient theme
    """

    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'modern-time-input',
            'autocomplete': 'off',
            'readonly': 'readonly',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs, format='%H:%M')

    def render(self, name, value, attrs=None, renderer=None):
        input_html = super().render(name, value, attrs, renderer)
        field_id = attrs.get('id', f'time_{uuid.uuid4().hex[:8]}')

        widget_html = f'''
        <div class="time-picker-wrapper">
            {input_html}
            <div id="{field_id}_modal" class="time-modal" style="display:none;">
                <div class="time-modal-overlay"></div>
                <div class="time-modal-content">
                    <div class="time-modal-header">
                        <h3>انتخاب زمان</h3>
                    </div>
                    <div class="time-picker-body">
                        <div class="time-column">
                            <div class="time-label">ساعت</div>
                            <div class="time-scroll" id="{field_id}_hour_scroll">
                                <div class="time-scroll-inner" id="{field_id}_hours"></div>
                            </div>
                        </div>
                        <div class="time-separator">:</div>
                        <div class="time-column">
                            <div class="time-label">دقیقه</div>
                            <div class="time-scroll" id="{field_id}_minute_scroll">
                                <div class="time-scroll-inner" id="{field_id}_minutes"></div>
                            </div>
                        </div>
                        <div class="time-column time-column-period">
                            <div class="time-label">نیمروز</div>
                            <div class="time-scroll" id="{field_id}_period_scroll">
                                <div class="time-scroll-inner" id="{field_id}_period"></div>
                            </div>
                        </div>
                    </div>
                    <div class="time-modal-footer">
                        <button type="button" class="time-btn time-btn-cancel">لغو</button>
                        <button type="button" class="time-btn time-btn-ok">تایید</button>
                    </div>
                </div>
            </div>
        </div>

        <style>
            .time-picker-wrapper {{
                position: relative;
                display: inline-block;
            }}

            .modern-time-input {{
                cursor: pointer;
                background: white;
                padding: 8px 12px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
                direction: ltr;
                text-align: left;
                width: 150px;
                transition: all 0.2s;
            }}

            .modern-time-input:hover {{
                border-color: #10b981;
            }}

            .modern-time-input:focus {{
                outline: none;
                border-color: #10b981;
                box-shadow: 0 0 0 0.2rem rgba(16, 185, 129, 0.25);
            }}

            .time-modal {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                z-index: 999999;
                display: flex;
                align-items: center;
                justify-content: center;
            }}

            .time-modal-overlay {{
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                backdrop-filter: blur(4px);
            }}

            .time-modal-content {{
                position: relative;
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                width: 420px;
                max-width: 90vw;
                overflow: hidden;
                animation: slideUp 0.3s ease-out;
            }}

            @keyframes slideUp {{
                from {{
                    opacity: 0;
                    transform: translateY(30px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}

            .time-modal-header {{
                background: linear-gradient(135deg, #10b981 0%, #3b82f6 100%);
                color: white;
                padding: 20px;
                text-align: center;
            }}

            .time-modal-header h3 {{
                margin: 0;
                font-size: 20px;
                font-weight: 600;
            }}

            .time-picker-body {{
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 30px 20px;
                gap: 15px;
                background: #f8f9fa;
            }}

            .time-column {{
                display: flex;
                flex-direction: column;
                align-items: center;
            }}

            .time-column-period {{
                width: 110px;
            }}

            .time-label {{
                font-size: 12px;
                color: #666;
                margin-bottom: 10px;
                font-weight: 600;
            }}

            .time-scroll {{
                width: 80px;
                height: 200px;
                overflow-y: scroll;
                position: relative;
                border: 2px solid #10b981;
                border-radius: 12px;
                background: white;
                scroll-behavior: smooth;
            }}

            .time-column-period .time-scroll {{
                width: 110px;
            }}

            .time-scroll::-webkit-scrollbar {{
                width: 8px;
            }}

            .time-scroll::-webkit-scrollbar-track {{
                background: #f1f1f1;
                border-radius: 10px;
            }}

            .time-scroll::-webkit-scrollbar-thumb {{
                background: linear-gradient(135deg, #10b981 0%, #3b82f6 100%);
                border-radius: 10px;
            }}

            .time-scroll::-webkit-scrollbar-thumb:hover {{
                background: linear-gradient(135deg, #059669 0%, #2563eb 100%);
            }}

            .time-scroll-inner {{
                padding: 84px 0;
            }}

            .time-item {{
                height: 40px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
                font-weight: 500;
                color: #999;
                cursor: pointer;
                transition: all 0.2s;
                user-select: none;
            }}

            .time-item:hover {{
                color: #10b981;
                background: rgba(16, 185, 129, 0.1);
            }}

            .time-item.selected {{
                color: #10b981;
                font-size: 22px;
                font-weight: 700;
                background: rgba(16, 185, 129, 0.15);
            }}

            .time-separator {{
                font-size: 36px;
                font-weight: bold;
                color: #10b981;
                margin: 0 5px;
                padding-bottom: 30px;
            }}

            .time-modal-footer {{
                padding: 20px;
                display: flex;
                gap: 12px;
                justify-content: flex-end;
                background: white;
                border-top: 1px solid #e9ecef;
            }}

            .time-btn {{
                padding: 10px 24px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-family: inherit;
                font-size: 14px;
                font-weight: 600;
                transition: all 0.2s;
                min-width: 80px;
            }}

            .time-btn-ok {{
                background: linear-gradient(135deg, #10b981 0%, #3b82f6 100%);
                color: white;
            }}

            .time-btn-ok:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
            }}

            .time-btn-cancel {{
                background: #6c757d;
                color: white;
            }}

            .time-btn-cancel:hover {{
                background: #5a6268;
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(108, 117, 125, 0.3);
            }}
        </style>

        <script>
        (function() {{
            const input = document.getElementById('{field_id}');
            const modal = document.getElementById('{field_id}_modal');
            const overlay = modal.querySelector('.time-modal-overlay');
            const hoursContainer = document.getElementById('{field_id}_hours');
            const minutesContainer = document.getElementById('{field_id}_minutes');
            const periodContainer = document.getElementById('{field_id}_period');
            const hourScroll = document.getElementById('{field_id}_hour_scroll');
            const minuteScroll = document.getElementById('{field_id}_minute_scroll');
            const periodScroll = document.getElementById('{field_id}_period_scroll');

            let selectedHour = 12;
            let selectedMinute = 0;
            let selectedPeriod = 'AM';

            // Initialize from existing value
            if (input.value) {{
                const parts = input.value.split(':');
                let hour = parseInt(parts[0]) || 0;
                selectedMinute = parseInt(parts[1]) || 0;

                if (hour >= 12) {{
                    selectedPeriod = 'PM';
                    selectedHour = hour === 12 ? 12 : hour - 12;
                }} else {{
                    selectedPeriod = 'AM';
                    selectedHour = hour === 0 ? 12 : hour;
                }}
            }}

            // Generate hours (1-12)
            for (let i = 1; i <= 12; i++) {{
                const div = document.createElement('div');
                div.className = 'time-item';
                div.textContent = i.toString().padStart(2, '0');
                div.dataset.value = i;
                div.addEventListener('click', function() {{
                    selectHour(i);
                }});
                hoursContainer.appendChild(div);
            }}

            // Generate minutes (0-59)
            for (let i = 0; i < 60; i++) {{
                const div = document.createElement('div');
                div.className = 'time-item';
                div.textContent = i.toString().padStart(2, '0');
                div.dataset.value = i;
                div.addEventListener('click', function() {{
                    selectMinute(i);
                }});
                minutesContainer.appendChild(div);
            }}

            // Generate AM/PM
            ['AM', 'PM'].forEach(period => {{
                const div = document.createElement('div');
                div.className = 'time-item';
                div.textContent = period === 'AM' ? 'قبل از ظهر' : 'بعد از ظهر';
                div.dataset.value = period;
                div.addEventListener('click', function() {{
                    selectPeriod(period);
                }});
                periodContainer.appendChild(div);
            }});

            function selectHour(hour) {{
                selectedHour = hour;
                updateSelection();
                scrollToSelected(hourScroll, hoursContainer, hour - 1);
            }}

            function selectMinute(minute) {{
                selectedMinute = minute;
                updateSelection();
                scrollToSelected(minuteScroll, minutesContainer, minute);
            }}

            function selectPeriod(period) {{
                selectedPeriod = period;
                updateSelection();
                scrollToSelected(periodScroll, periodContainer, period === 'AM' ? 0 : 1);
            }}

            function updateSelection() {{
                // Update hours
                hoursContainer.querySelectorAll('.time-item').forEach(item => {{
                    item.classList.toggle('selected', parseInt(item.dataset.value) === selectedHour);
                }});

                // Update minutes
                minutesContainer.querySelectorAll('.time-item').forEach(item => {{
                    item.classList.toggle('selected', parseInt(item.dataset.value) === selectedMinute);
                }});

                // Update period
                periodContainer.querySelectorAll('.time-item').forEach(item => {{
                    item.classList.toggle('selected', item.dataset.value === selectedPeriod);
                }});
            }}

            function scrollToSelected(scrollContainer, itemsContainer, index) {{
                const items = itemsContainer.querySelectorAll('.time-item');
                if (items[index]) {{
                    const itemHeight = 40;
                    scrollContainer.scrollTop = index * itemHeight;
                }}
            }}

            function openModal() {{
                modal.style.display = 'flex';
                updateSelection();

                // Scroll to selected values
                setTimeout(() => {{
                    scrollToSelected(hourScroll, hoursContainer, selectedHour - 1);
                    scrollToSelected(minuteScroll, minutesContainer, selectedMinute);
                    scrollToSelected(periodScroll, periodContainer, selectedPeriod === 'AM' ? 0 : 1);
                }}, 100);
            }}

            function closeModal() {{
                modal.style.display = 'none';
            }}

            function saveTime() {{
                let hour24 = selectedHour;

                if (selectedPeriod === 'PM' && selectedHour !== 12) {{
                    hour24 = selectedHour + 12;
                }} else if (selectedPeriod === 'AM' && selectedHour === 12) {{
                    hour24 = 0;
                }}

                const hourStr = hour24.toString().padStart(2, '0');
                const minuteStr = selectedMinute.toString().padStart(2, '0');
                input.value = hourStr + ':' + minuteStr;

                closeModal();
            }}

            // Event listeners
            input.addEventListener('click', function(e) {{
                e.preventDefault();
                e.stopPropagation();
                openModal();
            }});

            overlay.addEventListener('click', closeModal);

            modal.querySelector('.time-btn-ok').addEventListener('click', function(e) {{
                e.stopPropagation();
                saveTime();
            }});

            modal.querySelector('.time-btn-cancel').addEventListener('click', function(e) {{
                e.stopPropagation();
                closeModal();
            }});

            // Prevent modal content clicks from closing
            modal.querySelector('.time-modal-content').addEventListener('click', function(e) {{
                e.stopPropagation();
            }});
        }})();
        </script>
        '''

        return mark_safe(widget_html)
