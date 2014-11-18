// Createcluster confirm controller
App.CreateclusterConfirmController = Ember.Controller.extend({
	// in order to have access to create cluster controller
	needs : 'createclusterIndex',
	message : '',
	// return to previous screen (create cluster)
	go_back : function() {
		// reset some variables
		this.controllerFor('createclusterIndex').set('master_enabled', false);
		this.controllerFor('createclusterIndex').set('master_color', "lightblue");
		this.controllerFor('createclusterIndex').set('slaves_enabled', false);
		this.controllerFor('createclusterIndex').set('slaves_color', "lightblue");
		this.controllerFor('createclusterIndex').set('storage_Not_Allow', true);
	},
	actions : {
		// logout functionality
		logout : function() {
			// clear variables in create cluster
			this.controllerFor('createclusterIndex').reset_variables();
			// redirect to logout
			this.transitionTo('user.logout');
		},
		// when previous button is pressed
		// go_to_flavor action is triggered
		go_to_flavor : function() {
			this.set('message', '');
			this.go_back();
			// redirect
			this.transitionTo('createcluster.index');
		},
		// when next button is pressed
		// go_to_create action is triggered
		// User's cluster creation choices are send to backend for checking
		go_to_create : function() {
			var self = this;
			// PUT request
			var cluster_selection = this.store.update('clusterchoice', {
			  // set the clusterchoice model with the user choices
				'id' : 1,
				'cluster_name' : this.controllerFor('createclusterIndex').get('cluster_name'),
				'cluster_size' : this.controllerFor('createclusterIndex').get('cluster_size'),
				'cpu_master' : this.controllerFor('createclusterIndex').get('master_cpu_selection'),
				'mem_master' : this.controllerFor('createclusterIndex').get('master_mem_selection'),
				'disk_master' : this.controllerFor('createclusterIndex').get('master_disk_selection'),
				'cpu_slaves' : this.controllerFor('createclusterIndex').get('slaves_cpu_selection'),
				'mem_slaves' : this.controllerFor('createclusterIndex').get('slaves_mem_selection'),
				'disk_slaves' : this.controllerFor('createclusterIndex').get('slaves_disk_selection'),
				'disk_template' : this.controllerFor('createclusterIndex').get('disk_temp'),
				'os_choice' : this.controllerFor('createclusterIndex').get('operating_system')
			}).save();
			cluster_selection.then(function(data) {
				// Set the response to user's create cluster click when put succeeds.
				self.set('message', data._data.message);
			}, function() {
				// Set the response to user's create cluster click when put fails.
				self.set('message', 'A problem occured during your request. Please check your cluster parameters and try again');
			});
		}
	}
}); 