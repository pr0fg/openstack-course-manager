$( document ).ready(function() {
    check_cookie()
})

function check_cookie() {

  $.ajax({
    type: 'GET',
    url: '/api/public/token',
    statusCode: {
      401: function() {
        logout()
      }
    }
  })
  .done(function(data) {
    course = data.course
    $("#courseCode").html(course)
  })
}

function logout() {

  $.ajax({
    type: 'GET',
    url: '/api/logout',
  })
  .always(function(data) {
    document.cookie = "oscm=; expires=Thu, 01 Jan 1970 00:00:01 GMT; path=/; secure; samesite=strict";
    window.location.href = 'login.html'
  })

}
