// Please see documentation at https://docs.microsoft.com/aspnet/core/client-side/bundling-and-minification
// for details on configuring this project to bundle and minify static web assets.

// Write your JavaScript code.

window.SetCookie = function (name, value, days=365) {
    var expires = ""
    if (days) {
        var date = new Date()
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000))
        expires = "; expires=" + date.toGMTString()
    }
    document.cookie = name + "=" + value + expires + "; path=/"
}

window.GetCookies = function () {
    return document.cookie
}