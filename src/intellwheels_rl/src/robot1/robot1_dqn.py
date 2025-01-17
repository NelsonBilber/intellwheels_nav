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
from tools.train_dqn_log import TrainDQNLog

if __name__ == '__main__':
    rospy.init_node('robot1_dqn')

    #log file path 
    modelPath = os.path.dirname(os.path.realpath(__file__))
    modelPath = modelPath.replace('intellwheels_rl/src/robot1','intellwheels_rl/save_model')

    # log
    path_to_save_csv = modelPath + os.sep + "robot1_dqn.csv"
    traing_log = TrainDQNLog(path_to_save_csv)

    result = Float32MultiArray()
    get_action = Float32MultiArray()

    #parameters from launch files
    load_model = rospy.get_param('/robot1_dqn/load_model')
    start_from_episode =  rospy.get_param('/robot1_dqn/start_from_episode')
    total_episodes = rospy.get_param('/robot1_dqn/total_episodes')
    learning_rate =  rospy.get_param('/robot1_dqn/learning_rate')
    chair1_speed =  rospy.get_param('/robot1_dqn/chair1_speed')
    random_goal =  rospy.get_param('/robot1_dqn/random_goal')
    max_angular_speed =  rospy.get_param('/robot1_dqn/max_angular_speed')


    # training mode

    state_size = 12 # input of the network (12): 10 lidar samples + heading + current distance
    action_size = 5

    env = Env(action_size,chair1_speed, max_angular_speed , random_goal, "robot1_dqn_goal.csv", "robot1_dqn_trajectory.csv" )       
    agent = ReinforceAgentDQN(state_size, action_size, learning_rate, load_model, start_from_episode,
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

        print("Episdode: ", e)
        
        for t in range(agent.episode_step):
            action = agent.getAction(state)

            next_state, reward, collision, goal = env.step(action, e, t)

            agent.appendMemory(state, action, reward, next_state, collision)

            if len(agent.memory) >= agent.train_start:
                if global_step <= agent.target_update:
                    agent.trainModel()
                else:
                    agent.trainModel(True)

            score += reward
            state = next_state

            # save the model at 10 in 10 steps
            if e % 10 == 0:
                agent.model.save(agent.dirPath + str(e) + '.h5')
                with open(agent.dirPath + str(e) + '.json', 'w') as outfile:
                    json.dump(param_dictionary, outfile)
            

            if collision or goal:
                agent.updateTargetModel()
                scores.append(score)
                episodes.append(e)

                param_keys = ['epsilon']
                param_values = [agent.epsilon]
                param_dictionary = dict(zip(param_keys, param_values))
                break

            global_step += 1
            
            if global_step % agent.target_update == 0:
                rospy.loginfo("UPDATE TARGET NETWORK")

        m, s = divmod(int(time.time() - start_time), 60)
        h, m = divmod(m, 60)

        #rospy.loginfo('Ep: %d score: %.2f memory: %d epsilon: %.2f time: %d:%02d:%02d',
        #                e, score, len(agent.memory), agent.epsilon, h, m, s)

        # save log 

        f_time = str(h) + ":" + str(m)  + ":" + str(s)
        traing_log.save(e, score, np.max(agent.q_value), agent.epsilon, f_time, str(collision), str(goal))
    
        if agent.epsilon > agent.epsilon_min:
            agent.epsilon *= agent.epsilon_decay
        