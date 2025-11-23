var ClinicMaster = (function () {
    function d() {
        "undefined" != typeof skrollr &&
            (1191 <= window.innerWidth
                ? skrollr.init({ forceHeight: !1 })
                : skrollr.init().destroy());
    }
    function u() {
        function t(e, t) {
            0 < t.parent("li").has("ul").length &&
                (e.preventDefault(),
                    t.next(".sub-menu, .mega-menu").slideDown(),
                    t
                        .parent("li")
                        .siblings("li")
                        .children(".sub-menu, .mega-menu")
                        .slideUp()),
                t.parent().hasClass("open")
                    ? t
                        .parent("li")
                        .children(".sub-menu, .mega-menu")
                        .slideUp("slow", function () {
                            t.parent().removeClass("open");
                        })
                    : (t.hasClass("sub-menu") ||
                        t.parent().parent().find("li").removeClass("open"),
                        t.parent().addClass("open"));
        }
        f <= 991
            ? (jQuery(
                ".navbar-nav > li > a, .sub-menu > li > a, .navbar-nav > li > a > i, .sub-menu > li > a > i"
            )
                .unbind()
                .on({
                    click: function (e) {
                        t(e, jQuery(this));
                    },
                    keypress: function (e) {
                        if ("Enter" !== e.key) return !1;
                        t(e, jQuery(this));
                    },
                }),
                jQuery(".tabindex").attr("tabindex", "0"))
            : jQuery(".tabindex").removeAttr("tabindex");
    }
    function m() {
        var i = new Date(p).getTime(),
            s = setInterval(function () {
                var e, t, n, o, a, r;
                (e = new Date().getTime()),
                    (e = i - e),
                    (t = Math.floor(e / 864e5)),
                    (n = Math.floor((e % 864e5) / 36e5)),
                    (o = Math.floor((e % 36e5) / 6e4)),
                    (a = Math.floor((e % 6e4) / 1e3)),
                    (t = 1 == t.toString().length ? "0" + t : t),
                    (n = 1 == n.toString().length ? "0" + n : n),
                    (o = 1 == o.toString().length ? "0" + o : o),
                    (r = 1 == a.toString().length ? "0" + a : a),
                    jQuery("#day").text(t),
                    jQuery("#hour").text(n),
                    jQuery("#min").text(o),
                    jQuery("#second").text(r),
                    (t = 6 * a),
                    $(".round").css({ transform: "rotate(" + t + "deg)" }),
                    $(".round").css({ "-webkit-transform": "rotate(" + t + "deg)" }),
                    $(".round").css({ "-o-transform": "rotate(" + t + "deg)" }),
                    $(".round").css({ "-moz-transform": "rotate(" + t + "deg)" }),
                    $(".round").css({ "-ms-transform": "rotate(" + t + "deg)" }),
                    e < 0 &&
                    (clearInterval(s),
                        jQuery("#day, #hour, #min, #second").html("EXPIRED"));
            }, 1e3);
    }
    function y() {
        var e = jQuery(this),
            t = e.find(".modal-dialog");
        e.css("display", "block"),
            t.css(
                "margin-top",
                Math.max(0, (jQuery(window).height() - t.height()) / 2)
            );
    }
    var f = $(window).width(),
        p = new Date();
    p.setMonth(p.getMonth() + 1),
        (p =
            p.getDate() +
            " " +
            [
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ][p.getMonth()] +
            " " +
            p.getFullYear());
    return {
        init: function () {
            {
                let n = document.querySelector(".w3menu-toggler");
                if (n) {
                    let e = document.querySelector("body");
                    var o = document.querySelector(".menu-close"),
                        a = n.getAttribute("data-target");
                    let t = document.querySelector(a);
                    n.addEventListener("click", function () {
                        n.classList.add("open"),
                            e.classList.add("fixed"),
                            t.classList.add("show");
                    }),
                        o.addEventListener("click", function () {
                            n.classList.remove("open"),
                                e.classList.remove("fixed"),
                                t.classList.remove("show");
                        });
                }
            }
            {
                let n = document.querySelector(".toggle-tabs");
                if (n) {
                    let e = document.querySelectorAll(".pricingtable-price.year"),
                        t = document.querySelectorAll(".pricingtable-price.month");
                    e.forEach(function (e) {
                        e.style.display = "none";
                    });
                    (a = document.querySelector(".toggle-tabs .monthly")),
                        (o = document.querySelector(".toggle-tabs .yearly"));
                    a.addEventListener("click", function () {
                        n.classList.remove("yearly"),
                            n.classList.add("monthly"),
                            t.forEach(function (e) {
                                e.style.display = "block";
                            }),
                            e.forEach(function (e) {
                                e.style.display = "none";
                            });
                    }),
                        o.addEventListener("click", function () {
                            n.classList.remove("monthly"),
                                n.classList.add("yearly"),
                                t.forEach(function (e) {
                                    e.style.display = "none";
                                }),
                                e.forEach(function (e) {
                                    e.style.display = "block";
                                });
                        });
                }
            }
            {
                let t = document.querySelectorAll(".dz-flex-wrapper .dz-flex-item");
                t &&
                    t.forEach(function (e) {
                        e.addEventListener("click", function () {
                            t.forEach(function (e) {
                                e.classList.remove("active");
                            }),
                                e.classList.add("active");
                        });
                    });
            }
            var e, t, n, r;
            (n = document.getElementById("datePickerOnly")) &&
                new tempusDominus.TempusDominus(n, {
                    display: {
                        viewMode: "calendar",
                        components: {
                            decades: !0,
                            year: !0,
                            month: !0,
                            date: !0,
                            hours: !1,
                            minutes: !1,
                            seconds: !1,
                        },
                    },
                    localization: { locale: "fa", format: "dd/MM/yyyy", startOfTheWeek: 6, },
                }),
                (n = document.getElementById("timePickerOnly")) &&
                new tempusDominus.TempusDominus(n, {
                    display: {
                        viewMode: "clock",
                        components: {
                            decades: !1,
                            year: !1,
                            month: !1,
                            date: !1,
                            hours: !0,
                            minutes: !0,
                            seconds: !1,
                        },
                    },
                    localization: { locale: "fa", format: "HH:mm" },
                }),
                (n = document.getElementById("dateTimePickerOnly")) &&
                new tempusDominus.TempusDominus(n, {
                    display: {
                        viewMode: "calendar",
                        components: {
                            decades: !0,
                            year: !0,
                            month: !0,
                            date: !0,
                            hours: !0,
                            minutes: !0,
                            seconds: !1,
                        },
                    },
                    localization: { locale: "fa", format: "dd/MM/yyyy HH:mm", startOfTheWeek: 6, },
                });
            var i,
                s = new Date().getFullYear();
            for (i of document.getElementsByClassName("current-year"))
                i.innerHTML = s;
            (n = document.querySelectorAll(".dz-number")) &&
                n.forEach(function (t) {
                    t.addEventListener("input", function () {
                        var e = t.value.replace(/\D/g, "");
                        10 < e.length ? (t.value = e.slice(0, 10)) : (t.value = e);
                    });
                }),
                (n = document.getElementById("lightgallery")) &&
                lightGallery(n, {
                    plugins: [lgThumbnail, lgZoom],
                    selector: ".lg-item",
                    thumbnail: !0,
                    exThumbImage: "data-src",
                }),
                (n = document.querySelectorAll(".box-hover")) &&
                n.forEach(function (e) {
                    e.addEventListener("mouseenter", function () {
                        e.parentElement.parentElement
                            .querySelectorAll(".box-hover")
                            .forEach(function (e) {
                                e.classList.remove("active");
                            }),
                            e.classList.add("active");
                    });
                }),
                (n = document.querySelectorAll(".word-rotate")) &&
                n.forEach((e) => {
                    let t = e.textContent.split(""),
                        o = 360 / t.length;
                    var a = e.closest(".word-rotate-box");
                    t.forEach((e, t) => {
                        var n = document.createElement("span");
                        (n.className = "text__char"),
                            n.style.setProperty("--char-rotate", t * o + "deg"),
                            (n.textContent = e),
                            a.appendChild(n);
                    }),
                        e.remove();
                });
            {
                let e = document.querySelector(".scroltop");
                e &&
                    (window.addEventListener("scroll", function () {
                        500 < window.scrollY
                            ? e.classList.add("show")
                            : e.classList.remove("show");
                    }),
                        e.addEventListener("click", function () {
                            window.scrollTo({ top: 0, behavior: "smooth" });
                        }));
            }
            {
                let e = document.querySelector(".sticky-header");
                e &&
                    window.addEventListener("scroll", function () {
                        window.scrollY > e.offsetTop
                            ? e.classList.add("is-fixed")
                            : e.classList.remove("is-fixed");
                    });
            }
            0 < document.querySelectorAll(".wow").length &&
                ((e = new WOW({
                    boxClass: "wow",
                    animateClass: "animated",
                    offset: 50,
                    mobile: !1,
                })),
                    setTimeout(function () {
                        e.init();
                    }, 1500)),
                d(),
                u(),
                (n = parseInt($(".onepage").css("height"), 10)),
                $(".scroll")
                    .unbind()
                    .on("click", function (e) {
                        var t;
                        e.preventDefault(),
                            "" !== this.hash &&
                            ((e = this.hash),
                                (e = $(e).offset().top),
                                (t = parseInt($(".onepage").css("height"), 10)),
                                $("body").scrollspy({ target: ".navbar", offset: t + 2 }),
                                (e = e - t),
                                $("html, body").animate({ scrollTop: e }, 800, function () { }));
                    }),
                $("body").scrollspy({ target: ".navbar", offset: n + 2 }),
                (n = jQuery("#quik-search-btn")),
                (t = jQuery("#quik-search-remove")),
                n.on("click", function () {
                    jQuery(".dz-quik-search").fadeIn(500),
                        jQuery(".dz-quik-search").addClass("On");
                }),
                t.on("click", function () {
                    jQuery(".dz-quik-search").fadeOut(500),
                        jQuery(".dz-quik-search").removeClass("On");
                }),
                0 < jQuery(".mfp-gallery").length &&
                jQuery(".mfp-gallery").magnificPopup({
                    delegate: ".mfp-link",
                    type: "image",
                    tLoading: "Loading image #%curr%...",
                    mainClass: "mfp-img-mobile",
                    gallery: { enabled: !0, navigateByImgClick: !0, preload: [0, 1] },
                    image: {
                        tError:
                            '<a href="%url%">The image #%curr%</a> could not be loaded.',
                        titleSrc: function (e) {
                            return e.el.attr("title") + "<small></small>";
                        },
                    },
                }),
                0 < jQuery(".mfp-video").length &&
                jQuery(".mfp-video").magnificPopup({
                    type: "iframe",
                    iframe: {
                        markup:
                            '<div class="mfp-iframe-scaler"><div class="mfp-close"></div><iframe class="mfp-iframe" frameborder="0" allowfullscreen></iframe><div class="mfp-title">Some caption</div></div>',
                    },
                    callbacks: {
                        markupParse: function (e, t, n) {
                            t.title = n.el.attr("title");
                        },
                    },
                }),
                0 < jQuery(".popup-youtube, .popup-vimeo, .popup-gmaps").length &&
                $(".popup-youtube, .popup-vimeo, .popup-gmaps").magnificPopup({
                    disableOn: 700,
                    type: "iframe",
                    mainClass: "mfp-fade",
                    removalDelay: 160,
                    preloader: !1,
                    fixedContentPos: !0,
                }),
                document.querySelector(".quantity-input") &&
                jQuery(".quantity-input").TouchSpin({
                    verticalbuttons: !0,
                    verticalupclass: "fa-solid fa-plus",
                    verticaldownclass: "fa-solid fa-minus",
                }),
                jQuery('iframe[src*="youtube.com"]').wrap(
                    '<div class="embed-responsive embed-responsive-16by9"></div>'
                ),
                jQuery('iframe[src*="vimeo.com"]').wrap(
                    '<div class="embed-responsive embed-responsive-16by9"></div>'
                ),
                (n = p),
                0 < $(".countdown").length &&
                $(".countdown").countdown({ date: n + " 23:5" }, function () {
                    $(".countdown").text("we are live");
                }),
                jQuery(window).on("resize", function () {
                    jQuery(".modal:visible").each(y);
                }),
                jQuery(".modal").on("show.bs.modal", y),
                0 < jQuery(".bs-select").length && jQuery(".bs-select").selectpicker();
            for (
                var l = window.location,
                c = $("ul.navbar a")
                    .filter(function () {
                        return this.href == l;
                    })
                    .addClass("active")
                    .parent()
                    .addClass("active");
                c.is("li");

            )
                c = c.parent().addClass("show").parent("li").addClass("active");
            m(),
                (r = 0),
                $(window).scroll(function () {
                    var e;
                    f <= 768 &&
                        ($(this).scrollTop() + $(this).innerHeight() >=
                            document.querySelector("body").scrollHeight
                            ? $(".extra-nav").addClass("bottom-end")
                            : $(".extra-nav").removeClass("bottom-end"),
                            (e = $(this).scrollTop()),
                            r < e
                                ? $(".extra-nav").addClass("active")
                                : $(".extra-nav").removeClass("active"),
                            (r = e));
                });

        },
        load: function () {
            var t, e, n, o;
            jQuery(".counter").length &&
                jQuery(".counter").counterUp({ delay: 10, time: 3e3 }),
                0 < jQuery("#masonry, .masonry").length &&
                (jQuery(".filters li").removeClass("active"),
                    jQuery(".filters li:first").addClass("active"),
                    (t = jQuery("#masonry, .masonry")),
                    0 < jQuery(".card-container").length) &&
                (t.data("gutter"),
                    (e = void 0 === t.data("gutter") ? 0 : t.data("gutter")),
                    (e = parseInt(e)),
                    "" !=
                    (n =
                        void 0 === t.attr("data-column-width")
                            ? ""
                            : t.attr("data-column-width")) && (n = parseInt(n)),
                    t.imagesLoaded(function () {
                        t.masonry({
                            gutter: e,
                            columnWidth: n,
                            isAnimated: !0,
                            itemSelector: ".card-container",
                        });
                    })),
                0 < jQuery(".filters").length &&
                (jQuery(".filters li:first").addClass("active"),
                    jQuery(".filters li").on("click", function () {
                        jQuery(".filters li").removeClass("active"),
                            jQuery(this).addClass("active");
                        var e = $(this).attr("data-filter");
                        t.isotope({ filter: e });
                    })),
                0 < $(".twentytwenty-container").length &&
                $(
                    ".twentytwenty-container[data-orientation!='vertical']"
                ).twentytwenty({ default_offset_pct: 0.5 }),
                0 < jQuery("#Isotope, .isotope").length &&
                (o = jQuery("#Isotope, .isotope")).isotope({
                    itemSelector: ".card-container",
                    layoutMode: "fitRows",

                }),
                0 < jQuery(".filter-isotope").length &&
                (jQuery(".filter-isotope li:first").addClass("active"),
                    jQuery(".filter-isotope li").on("click", function () {
                        jQuery(".filter-isotope li").removeClass("active"),
                            jQuery(this).addClass("active");
                        var e = $(this).attr("data-filter");
                        o.isotope({ filter: e });
                    })),
                jQuery(".modal").on("show.bs.modal", y);
        },
        resize: function () {
            var e, t;
            (f = $(window).width()),
                u(),
                (t = e = 0),
                $(".header .sticky-header").removeClass("is-fixed"),
                $(".header").removeAttr("style"),
                0 < jQuery(".header .top-bar").length &&
                991 < f &&
                (e = parseInt($(".header .top-bar").outerHeight())),
                (t =
                    (t =
                        0 < jQuery(".header").length
                            ? 0 == (t = parseInt($(".header").height()))
                                ? parseInt($(".header .main-bar").outerHeight())
                                : t
                            : t) + e),
                jQuery(".header").css("height", t),
                d();
        },
    };
})();
document.addEventListener("DOMContentLoaded", function () {
    ClinicMaster.init(),
        setTimeout(function () {
            var e = document.getElementById("dzPreloader");
            e &&
                ((e.style.transition = "opacity 0.5s"),
                    (e.style.opacity = 0),
                    setTimeout(function () {
                        e.style.display = "none";
                    }, 500));
        }, 1500),
        $(".cart-widget .dz-close").on("click", function () {
            $(this)
                .closest(".sidebar-cart-list li")
                .fadeOut("normal", function () {
                    $(this).remove();
                });
        });
}),
    window.addEventListener("load", function () {
        ClinicMaster.load(),
            document.body.addEventListener("keydown", function () {
                document.body.classList.add("show-focus-outline");
            }),
            document.body.addEventListener("mousedown", function () {
                document.body.classList.remove("show-focus-outline");
            });
    }),
    window.addEventListener("resize", function () {
        ClinicMaster.resize();
    });
