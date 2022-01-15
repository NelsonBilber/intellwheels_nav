#!/usr/bin/env python

import rospy
import os
import json
import numpy as np
import random
import time
import ast

import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from collections import deque
from std_msgs.msg import Float32MultiArray
from std_msgs.msg import Float64

from robot2.robot2_environment import Env
from algorithms.qlearn import QLearn


def __numpy_to_string(A):
    return str(round(np.sum(A), 3))

if __name__ == '__main__':
    rospy.init_node('robot2_qlearn_2')

    state_size = 12 # 
    action_size = 5
    
    env = Env(action_size)
    last_time_steps = np.ndarray(0)

    '''
    Alpha = rospy.get_param("/alpha")
    Epsilon = rospy.get_param("/epsilon")
    Gamma = rospy.get_param("/gamma")
    epsilon_discount = rospy.get_param("/epsilon_discount")
    nepisodes = rospy.get_param("/nepisodes")
    nsteps = rospy.get_param("/nsteps")
    '''

    Alpha = 0.1
    Epsilon = 0.7
    Gamma = 0.9
    epsilon_discount = 0.999
    nepisodes = 100000
    nsteps = 1000

    qlearn = QLearn(actions=range(action_size),alpha=Alpha, gamma=Gamma, epsilon=Epsilon)

    initial_epsilon = qlearn.epsilon
    start_time = time.time()
    highest_reward = 0

    for x in range(nepisodes):
        cumulated_reward = 0
        collision = False
        if qlearn.epsilon > 0.05:
            qlearn.epsilon *= epsilon_discount
       
        state = env.reset()
        state = __numpy_to_string(state)
               
        # for each episode, we test the robot for nsteps
        for i in range(nsteps):
            
            print("Episode: ", x, " Step: ", i)

            # Pick an action based on the current state
            action = qlearn.chooseAction(state)
            
            nextState, reward, collision, goal = env.step(action)
            nextState = __numpy_to_string(nextState)

            cumulated_reward += reward
            if highest_reward < cumulated_reward:
                highest_reward = cumulated_reward

            #rospy.logdebug("env.get_state...==>" + str(nextState))

            # Make the algorithm learn based on the results
            #print("Types..................")
            #print("Episode: ", x, " Step: ", i)
            #print("state: ",  type(state) , " ", state   )
            #print("action: ", type(action), "  ", action)
            #print("reward: ", type(reward), " " , reward )
            #print("nextState: ", type(nextState), " ", nextState)
            #print("")

            qlearn.learn(state, action, reward, nextState)

            if not(collision):
                state = nextState
            else:
                rospy.logdebug("DONE EPISODE!")
                last_time_steps = np.append(last_time_steps, [int(i + 1)])
                break

            #rospy.logdebug("###################### END Step...["+str(i)+"]")

        m, s = divmod(int(time.time() - start_time), 60)
        h, m = divmod(m, 60)
        rospy.logwarn( ("EP: "+str(x+1)+" - [alpha: "+str(round(qlearn.alpha,2))+" - gamma: "+str(round(qlearn.gamma,2))+" - epsilon: "+str(round(qlearn.epsilon,2))+"] - Reward: "+str(cumulated_reward)+"     Time: %d:%02d:%02d" % (h, m, s)))

    rospy.loginfo ( ("\n|"+str(nepisodes)+"|"+str(qlearn.alpha)+"|"+str(qlearn.gamma)+"|"+str(initial_epsilon)+"*"+str(epsilon_discount)+"|"+str(highest_reward)+"| PICTURE |"))

    l = last_time_steps.tolist()
    l.sort()

    #print("Parameters: a="+str)
    print("Overall score: {:0.2f}".format(last_time_steps.mean()))
    print("Best 100 score: {:0.2f}".format(reduce(lambda x, y: x + y, l[-100:]) / len(l[-100:])))

    env.close()