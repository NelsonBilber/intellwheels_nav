#!/usr/bin/env python

import rospy
import os
import os.path
import json
import numpy as np
import random
import time
import pandas as pd

from datetime import datetime

import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from collections import deque
from std_msgs.msg import Float32MultiArray
from robot1.robot1_environment import Env

from algorithms.dqn import ReinforceAgentDQN
from tools.train_log import TrainLog

if __name__ == '__main__':
    rospy.init_node('robot1_dqn')

    #log file path 
    modelPath = os.path.dirname(os.path.realpath(__file__))
    modelPath = modelPath.replace('intellwheels_rl/src/robot1','intellwheels_rl/save_model')

    # log
    path_to_save_csv = modelPath + os.sep + "robot1_dqn.csv"
    traing_log = TrainLog(path_to_save_csv)

    # publish results
    pub_result = rospy.Publisher('result', Float32MultiArray, queue_size=5)
    pub_get_action = rospy.Publisher('get_action', Float32MultiArray, queue_size=5)
    
    result = Float32MultiArray()
    get_action = Float32MultiArray()

    #parameters from launch files
    load_model = rospy.get_param('/robot1_dqn/load_model')
    start_from_episode =  rospy.get_param('/robot1_dqn/start_from_episode')
    total_episodes = rospy.get_param('/robot1_dqn/total_episodes')

    # training mode

    state_size = 12 # input of the network (12): 10 lidar samples + heading + current distance
    action_size = 5

    env = Env(action_size, True)       
    agent = ReinforceAgentDQN(state_size, action_size, load_model, start_from_episode,
             'intellwheels_rl/src/algorithms', 'intellwheels_rl/save_model/robot1_dqn_')

    scores, episodes = [], []
    global_step = 0
    start_time = time.time()

    rospy.loginfo("+++++++++++++++++++++++++++++++++++++++++++++++++++++")

    if agent.load_model:
        rospy.loginfo("START TRAINING MODEL FROM episode = %d", agent.load_episode)
    else:
        rospy.loginfo("START TRAINING MODEL FROM scratch") 
    
    rospy.loginfo("=====================================================")
    
    # Determine the number of the starting episode
    if agent.load_model == False:
        load_episode = 0
    else:
        load_episode = agent.load_episode
    
    
    # Run every new episode
    for e in range(agent.load_episode + 1, total_episodes):
        done = False
        state = env.reset()
        score = 0
        for t in range(agent.episode_step):
            action = agent.getAction(state)

            print("Episdode: ", e , " Step: ", t)

            next_state, reward, collision, goal = env.step(action, e, t)

            #print("Types..................")
            #print("state: ",  type(state) , " ", state   )
            #print("action: ", type(action), "  ", action)
            #print("reward: ", type(reward), " " , reward )
            #print("nextState: ", type(next_state), " ", next_state)
            #print("")

            agent.appendMemory(state, action, reward, next_state, collision)

            if len(agent.memory) >= agent.train_start:
                if global_step <= agent.target_update:
                    agent.trainModel()
                else:
                    # Prediction using  '.model'
                    agent.trainModel(True)

            score += reward
            state = next_state

            get_action.data = [action, score, reward]
            pub_get_action.publish(get_action)

            # save the model at 10 in 10 steps
            if e % 10 == 0:
                agent.model.save(agent.dirPath + str(e) + '.h5')
                with open(agent.dirPath + str(e) + '.json', 'w') as outfile:
                    json.dump(param_dictionary, outfile)
            
            timeout = False
            if t >= 500:
                rospy.loginfo("Time out!!")
                timeout = True

            if collision or timeout:
                # publish results
                result.data = [score, np.max(agent.q_value)]
                pub_result.publish(result)
                
                agent.updateTargetModel()
                scores.append(score)
                episodes.append(e)

                m, s = divmod(int(time.time() - start_time), 60)
                h, m = divmod(m, 60)
                
                rospy.loginfo('Ep: %d score: %.2f memory: %d epsilon: %.2f time: %d:%02d:%02d',
                              e, score, len(agent.memory), agent.epsilon, h, m, s)

                # save log              

                data_csv = [[ e, score, np.max(agent.q_value) ,len(agent.memory)
                            , agent.epsilon, str(h) + ":" + str(m)  + ":" + str(s) 
                            , str(timeout) , str(collision) , str(goal) ]]

                traing_log.save(data_csv)

                param_keys = ['epsilon']
                param_values = [agent.epsilon]
                param_dictionary = dict(zip(param_keys, param_values))
                break

            global_step += 1
            
            if global_step % agent.target_update == 0:
                rospy.loginfo("UPDATE TARGET NETWORK")
    
        if agent.epsilon > agent.epsilon_min:
            agent.epsilon *= agent.epsilon_decay
        