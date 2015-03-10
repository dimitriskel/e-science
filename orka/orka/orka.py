#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""orka.orka: provides entry point main()."""
import logging
from sys import argv
from kamaki.clients import ClientError
from cluster_errors_constants import *
from argparse import ArgumentParser, ArgumentTypeError 
from version import __version__
from utils import ClusterRequest, ConnectionError, authenticate_escience, get_user_clusters, \
    custom_sort_factory, custom_sort_list, custom_date_format, get_from_kamaki_conf
from time import sleep
import sys


class _ArgCheck(object):
    """
    Used for type checking arguments supplied for use with type= and
    choices= argparse attributes
    """

    def __init__(self):
        self.logging_levels = {
            'critical': logging.CRITICAL,
            'error': logging.ERROR,
            'warning': logging.WARNING,
            'summary': SUMMARY,
            'report': REPORT,
            'info': logging.INFO,
            'debug': logging.DEBUG,
        }
        logging.addLevelName(REPORT, "REPORT")
        logging.addLevelName(SUMMARY, "SUMMARY")

    def positive_num_is(self, val):
        """
        :param val: int
        :return: val if val > 0 or raise exception
        """
        ival = int(val)
        if ival <= 0:
            raise ArgumentTypeError(" %s must be a positive number." % val)
        return ival

    def two_or_larger_is(self, val):
        """
        :param val: int
        :return: val if > 2 or raise exception
        """
        ival = int(val)
        if ival < 2:
            raise ArgumentTypeError(" %s must be at least 2." % val)
        return ival

    def five_or_larger_is(self, val):
        ival = int(val)
        if ival < 5:
            raise ArgumentTypeError(" %s must be at least 5." % val)
        return ival
    
    def a_number_is(self, val):
        """
        :param val: str
        :return val if it contains only numbers
        """
        if val.isdigit():
            return val
        else:
            raise ArgumentTypeError(" %s must be a number." % val)
        
    def a_string_is(self, val):
        """
        :param val: str
        :return val if it contains at least one letter
        """
        if not val.isdigit():
            return val
        else:
            raise ArgumentTypeError(" %s must containt at least one letter." % val)


def task_message(task_id, escience_token, wait_timer, cli_message=' Waiting for cluster status update...'):
    """
    Function to check create and destroy celery tasks running from orka-CLI
    and log task state messages.
    """
    payload = {"job":{"task_id": task_id}}
    yarn_cluster_logger = ClusterRequest(escience_token, payload, action='job')
    previous_response = {'job':{'state':'placeholder'}}
    response = yarn_cluster_logger.retrieve()

    while 'state' in response['job']:
        if response['job']['state'].split('%',1)[0].replace('\r','') != previous_response['job']['state'].split('%',1)[0].replace('\r',''):
            sys.stdout.write('{0}\r'.format(response['job']['state']))
            previous_response = response
        else:
            sleep(wait_timer)
        response = yarn_cluster_logger.retrieve()
        sys.stdout.flush()

    if 'success' in response['job']:
        return response['job']['success']

    elif 'error' in response['job']:
        logging.error(response['job']['error'])
        exit(error_fatal)



class HadoopCluster(object):
    """Wrapper class for YarnCluster."""
    def __init__(self, opts):
        self.opts = opts
        try: 
            self.escience_token = authenticate_escience(self.opts['token'])
        except ConnectionError:
            logging.error(' e-science server unreachable or down.')
            exit(error_fatal)
        except ClientError:
            logging.error(' Authentication error with token: ' + self.opts['token'])
            exit(error_fatal)
        

    def create(self):
        """ Method for creating Hadoop clusters in~okeanos."""
        try:
            payload = {"clusterchoice":{"project_name": self.opts['project_name'], "cluster_name": self.opts['name'],
                                        "cluster_size": self.opts['cluster_size'],
                                        "cpu_master": self.opts['cpu_master'], "mem_master": self.opts['ram_master'],
                                        "disk_master": self.opts['disk_master'], "cpu_slaves": self.opts['cpu_slave'],
                                        "mem_slaves": self.opts['ram_slave'], "disk_slaves": self.opts['disk_slave'],
                                        "disk_template": self.opts['disk_template'], "os_choice": self.opts['image']}}
            yarn_cluster_req = ClusterRequest(self.escience_token, payload, action='cluster')
            response = yarn_cluster_req.create_cluster()
            if 'task_id' in response['clusterchoice']:
                task_id = response['clusterchoice']['task_id']
            else:
                logging.error(response['clusterchoice']['message'])
                exit(error_fatal)
            result = task_message(task_id, self.escience_token, wait_timer_create)
            logging.log(SUMMARY, " Yarn Cluster is active.You can access it through " +
                        result['master_IP'] + ":8088/cluster")
            logging.log(SUMMARY, " The root password of your master VM is " + result['master_VM_password'])


        except Exception, e:
            logging.error(' Fatal error: ' + str(e.args[0]))
            exit(error_fatal)


    def destroy(self):
        """ Method for deleting Hadoop clusters in~okeanos."""
        clusters = get_user_clusters(self.opts['token'])
        for cluster in clusters:
            if (cluster['id'] == self.opts['cluster_id']) and cluster['cluster_status'] == '1':
                break
        else:
            logging.error(' Only active clusters can be destroyed.')
            exit(error_fatal)
        try:
            payload = {"clusterchoice":{"id": self.opts['cluster_id']}}
            yarn_cluster_req = ClusterRequest(self.escience_token, payload, action='cluster')
            response = yarn_cluster_req.delete_cluster()
            task_id = response['clusterchoice']['task_id']
            result = task_message(task_id, self.escience_token, wait_timer_delete)
            logging.log(SUMMARY, ' Cluster with name "%s" and all its resources deleted' %(result))
        except Exception, e:
            logging.error(' Error:' + str(e.args[0]))
            exit(error_fatal)
            

    def hadoop_action(self):
        """ Method for applying an action to a Hadoop cluster"""
        action = str.lower(self.opts['hadoop_status'])
        clusters = get_user_clusters(self.opts['token'])
        active_cluster = None
        for cluster in clusters:
            if (cluster['id'] == self.opts['cluster_id']):
                active_cluster = cluster
                if cluster['cluster_status'] == '1':
                    break
        else:
            logging.error(' Hadoop can only be managed for an active cluster.')
            exit(error_fatal)
        if active_cluster:            
            if (active_cluster['hadoop_status'] == "1" and action == "start"):
                logging.error(' Hadoop already started.')
                exit(error_fatal)
            elif (active_cluster['hadoop_status'] == "0" and action == "stop"):
                logging.error(' Hadoop already stopped.')
                exit(error_fatal)
        try:
            payload = {"clusterchoice":{"id": self.opts['cluster_id'], "hadoop_status": action}}
            yarn_cluster_req = ClusterRequest(self.escience_token, payload, action='cluster')
            response = yarn_cluster_req.create_cluster()
            task_id = response['clusterchoice']['task_id']
            result = task_message(task_id, self.escience_token, wait_timer_delete)
            logging.log(SUMMARY, result)
        except Exception, e:
            logging.error(' Error:' + str(e.args[0]))
            exit(error_fatal)
                    
    def put(self):
        """ Method for putting files to Hadoop clusters in~okeanos."""
        clusters = get_user_clusters(self.opts['token'])
        for cluster in clusters:
            if (cluster['id'] == self.opts['cluster_id']) and cluster['cluster_status'] == '1':
                break
        else:
            logging.error(' You can upload files to active clusters only.')
            exit(error_fatal)
        try:
            # hard-coded for testing the file transfer
            self.opts['source']='https://dumps.wikimedia.org/elwiki/latest/elwiki-latest-pages-meta-current.xml.bz2'
            self.opts['destination']='hadoopwiki'
            payload = {"hdfs":{"id": self.opts['cluster_id'], "source": self.opts['source'],
                                        "dest": self.opts['destination'], "user": self.opts['user'],
                                        "password": self.opts['password']}}
            # payload = {"hdfs":self.opts}.....needs to change cluster_id->id for this to work.
            yarn_cluster_req = ClusterRequest(self.escience_token, payload, action='hdfs')
            response = yarn_cluster_req.post()
            if 'task_id' in response['hdfs']:
                task_id = response['hdfs']['task_id']
            else:
                logging.error(response['hdfs']['message'])
                exit(error_fatal)
            result = task_message(task_id, self.escience_token, wait_timer_delete,
                                  cli_message=' Waiting for file transfer status update...')
            if result == 0:
                logging.log(SUMMARY, ' Transfered file to Hadoop filesystem')
        except Exception, e:
            logging.error(' Error:' + str(e.args[0]))
            exit(error_fatal)


class UserClusterInfo(object):
    """ Class holding user cluster info
    sortdict: input a cluster dictionary, output cluster with keys sorted according to order
    sortlist: input a clusters list of cluster dictionaries, output a clusters list sorted according to cluster key
    list: pretty printer
    """
    def __init__(self, opts):
        self.opts = opts
        self.data = list()
        self.cluster_list_order = [['cluster_name','id','action_date','cluster_size','cluster_status','hadoop_status',
                            'master_IP','project_name','os_image','disk_template',
                            'cpu_master','mem_master','disk_master',
                            'cpu_slaves','mem_slaves','disk_slaves']]
        self.sort_cluster_func = custom_sort_factory(self.cluster_list_order)
        self.cluster_short_list = {'id':True, 'cluster_name':True, 'action_date':True, 'cluster_size':True,
                                   'cluster_status':True, 'hadoop_status':True, 'master_IP':True}
        self.cluster_skip_list = {'task_id':True, 'state':True}
        self.status_desc_to_status_id = {'ACTIVE':'1', 'PENDING':'2', 'DESTROYED':'0'}
        self.status_id_to_status_desc = {'1':'ACTIVE', '2':'PENDING', '0':'DESTROYED'}
        self.hdp_status_id_to_status_desc = {'0':'STOPPED','1':'STARTED','2':'FORMAT'}
        self.hdp_status_desc_to_status_id = {'STOPPED':'0','STARTED':'1','FORMAT':'2'}
        self.disk_template_to_label = {'ext_vlmc':'Archipelago', 'drbd':'Standard'}
        self.clusters_list_order = ['id']

    def sortdict(self, cluster):
        return self.sort_cluster_func(cluster)
    
    def sortlist(self, clusters, keys):
        return custom_sort_list(clusters, keys)
    
    def list(self):
        try:
            self.data.extend(get_user_clusters(self.opts['token']))
        except ClientError, e:
            logging.error(e.message)
            exit(error_fatal)
        except Exception, e:
            logging.error(str(e.args[0]))
            exit(error_fatal)
        
        opt_short = not self.opts['verbose']
        opt_status = False
        opt_cluster_id = self.opts.get('cluster_id',False)
        cluster_count = 0
        if self.opts['status']:
            opt_status = self.status_desc_to_status_id[self.opts['status'].upper()]
        
        if len(self.data) > 0:
            sorted_cluster_list = self.sortlist(self.data, self.clusters_list_order)
            for cluster in sorted_cluster_list:
                if opt_status and cluster['cluster_status'] != opt_status:
                    continue
                if opt_cluster_id and cluster['id'] != opt_cluster_id:
                    continue
                cluster_count += 1
                sorted_cluster = self.sortdict(cluster)
                for key in sorted_cluster:
                    if (opt_short and not self.cluster_short_list.has_key(key)) or self.cluster_skip_list.has_key(key):
                        continue
                    if key == 'cluster_name':
                        fmt_string = '{:<5}' + key + ': {' + key + '}'
                    elif key == 'cluster_status':
                        fmt_string = '{:<10}' + key + ': ' + self.status_id_to_status_desc[sorted_cluster[key]]
                    elif key == 'hadoop_status':
                        fmt_string = '{:<10}' + key + ': ' + self.hdp_status_id_to_status_desc[sorted_cluster[key]]
                    elif key == 'disk_template':
                        fmt_string = '{:<10}' + key + ': ' + self.disk_template_to_label[sorted_cluster[key]]
                    elif key == 'action_date':
                        fmt_string = '{:<10}' + key + ': ' + custom_date_format(sorted_cluster[key])
                    else:
                        fmt_string = '{:<10}' + key + ': {' + key + '}'
                    print fmt_string.format('',**sorted_cluster)
                print ''
            if cluster_count == 0:
                print 'No cluster(s) found matching those options.'
        else:
            print 'No user cluster Information available.'

def main():
    """
    Entry point of orka package. Parses user arguments and return
    appropriate messages for success or error.
    """
    parser = ArgumentParser(description='Create or Destroy a Hadoop-Yarn'
                                        ' cluster in ~okeanos')
    checker = _ArgCheck()
    logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',
                                level=checker.logging_levels['summary'],
                                datefmt='%H:%M:%S')
    try:
        kamaki_token = get_from_kamaki_conf('cloud "~okeanos"', 'token')
    except ClientError, e:
        kamaki_token = ' '
        logging.warning(e.message)
    
    subparsers = parser.add_subparsers(help='Choose Hadoop cluster action'
                                            ' create or destroy')
    parser.add_argument("-V", "--version", action='version',
                        version=('orka %s' % __version__))
    parser_c = subparsers.add_parser('create',
                                     help='Create a Hadoop-Yarn cluster'
                                     ' on ~okeanos.')
    parser_d = subparsers.add_parser('destroy',
                                     help='Destroy a Hadoop-Yarn cluster'
                                     ' on ~okeanos.')
    parser_i = subparsers.add_parser('list',
                                     help='List user clusters.')
    parser_n = subparsers.add_parser('info',
                                     help='Information for a specific Hadoop-Yarn cluster.')    
    parser_h = subparsers.add_parser('hadoop', 
                                     help='Start or Stop a Hadoop-Yarn cluster')
    parser_p = subparsers.add_parser('put', 
                                     help='Put/Upload a file on a Hadoop-Yarn filesystem')    
    if len(argv) > 1:

        parser_c.add_argument("name", help='The specified name of the cluster.'
                              ' Will be prefixed by [orka]', type=checker.a_string_is)

        parser_c.add_argument("cluster_size", help='Total number of cluster nodes',
                              type=checker.two_or_larger_is)

        parser_c.add_argument("cpu_master", help='Number of CPU cores for the master node',
                              type=checker.positive_num_is)

        parser_c.add_argument("ram_master", help='Size of RAM (MB) for the master node',
                              type=checker.positive_num_is)

        parser_c.add_argument("disk_master", help='Disk size (GB) for the master node',
                              type=checker.five_or_larger_is)

        parser_c.add_argument("cpu_slave", help='Number of CPU cores for the slave node(s)',
                              type=checker.positive_num_is)

        parser_c.add_argument("ram_slave", help='Size of RAM (MB) for the slave node(s)',
                              type=checker.positive_num_is)

        parser_c.add_argument("disk_slave", help='Disk size (GB) for the slave node(s)',
                              type=checker.five_or_larger_is)

        parser_c.add_argument("disk_template", help='Disk template (choices: {%(choices)s})',
                              metavar='disk_template', choices=['Standard', 'Archipelago'], 
                              type=str.capitalize)

        parser_c.add_argument("project_name", help='~okeanos project name'
                              ' to request resources from ', type=checker.a_string_is)

        parser_c.add_argument("--image", help='OS for the cluster.'
                              ' Default is "Debian Base"', metavar='image',
                              default=default_image)

        parser_c.add_argument("--use_hadoop_image", help='Use a pre-stored hadoop image for the cluster.'
                              ' Default is HadoopImage (overrides image selection)',
                              nargs='?', metavar='hadoop_image_name', default=None,
                              const='Hadoop-2.5.2')

        parser_c.add_argument("--auth_url", metavar='auth_url', default=auth_url,
                              help='Synnefo authentication url. Default is ' +
                              auth_url)       
        parser_c.add_argument("--token", metavar='token', default=kamaki_token, type=checker.a_string_is,
                              help='Synnefo authentication token. Default read from .kamakirc')


        parser_d.add_argument('cluster_id',
                              help='The id of the Hadoop cluster', type=checker.positive_num_is)
        parser_d.add_argument("--token", metavar='token', default=kamaki_token, type=checker.a_string_is,
                              help='Synnefo authentication token. Default read from .kamakirc')

       
        parser_i.add_argument('--status', help='Filter by status ({%(choices)s})'
                              ' Default is all: no filtering.', type=str.upper,
                              metavar='status', choices=['ACTIVE','DESTROYED','PENDING'])
        
        parser_i.add_argument('--verbose', help='List extra cluster details.',
                              action="store_true")
        parser_i.add_argument("--token", metavar='token', default=kamaki_token, type=checker.a_string_is,
                              help='Synnefo authentication token. Default read from .kamakirc')         
        
        
        parser_h.add_argument('hadoop_status', 
                              help='Hadoop status (choices: {%(choices)s})', type=str.lower,
                              metavar='hadoop_status', choices=['start', 'format', 'stop'])
        parser_h.add_argument('cluster_id',
                              help='The id of the Hadoop cluster', type=checker.positive_num_is)
        parser_h.add_argument("--token", metavar='token', default=kamaki_token, type=checker.a_string_is,
                              help='Synnefo authentication token. Default read from .kamakirc')
        
        
        parser_n.add_argument('cluster_id',
                                 help='The id of the Hadoop cluster', type=checker.positive_num_is)
        parser_n.add_argument("--token", metavar='token', default=kamaki_token, type=checker.a_string_is,
                              help='Synnefo authentication token. Default read from .kamakirc')

        parser_p.add_argument('cluster_id',
                              help='The id of the Hadoop cluster', type=checker.positive_num_is)
        parser_p.add_argument('source',
                              help='The file to be uploaded')
        parser_p.add_argument('destination',
                              help='Destination in the Hadoop filesystem')
        parser_p.add_argument("--token", metavar='token', default=kamaki_token, type=checker.a_string_is,
                              help='Synnefo authentication token. Default read from .kamakirc')
        parser_p.add_argument('--user',
                              help='Ftp-Http remote user')
        parser_p.add_argument('--password',
                              help='ftp-http password')
                
        opts = vars(parser.parse_args(argv[1:]))
        verb = argv[1]
        if verb == 'create':
            if opts['use_hadoop_image']:
                opts['image'] = opts['use_hadoop_image']
        elif verb == 'info':
            opts['verbose'] = True
            opts['status'] = None

    else:
        logging.error('No arguments were given')
        parser.parse_args(' -h'.split())
        exit(error_no_arguments)
    c_hadoopcluster = HadoopCluster(opts)
    c_userclusters = UserClusterInfo(opts)
    if verb == 'create':
        c_hadoopcluster.create()

    elif verb == 'destroy':
        c_hadoopcluster.destroy()
        
    elif verb == 'list' or verb == 'info':
        c_userclusters.list()
        
    elif verb == 'hadoop':
        c_hadoopcluster.hadoop_action()

    elif argv[1] == 'put':
        c_hadoopcluster.put()

if __name__ == "__main__":
    main()