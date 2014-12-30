// Login route
// If user is logged in, redirect to welcome screen
App.UserLoginRoute = Ember.Route.extend({
	redirect : function() {
		if (this.controllerFor('user.login').isLoggedIn()) {
			this.transitionTo('user.welcome');
		}
	}
});