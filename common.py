from typing import List, Tuple
import numpy as np
import os


def read_instance_from_txt(file_name:str):
    starts=[]
    goals=[]
    return starts,goals


def read_paths_from_txt(file_name:str):
    paths=[]
    width=0
    height=0
    with open(file_name, "r") as file_content:
        lines=file_content.readlines()
        for line in lines:
            wh_line=line.split('=')
            if len(wh_line)==2:
                if wh_line[0]=='width':
                    width=int(wh_line[1])
                    continue
                if wh_line[0]=='height':
                    height=int(wh_line[1])
                    continue
                
            path_line=line.split(':')
            if len(path_line)<2:
                continue
            pi=[]
            path_strings=path_line[1].split('),')
            
            for vs in path_strings:
                xy_string=vs[1:].split(',')
                if len(xy_string)<2:
                    continue
                x=int(xy_string[0])
                y=int(xy_string[1])
                pi.append((x,y))
            paths.append(pi)
    return paths,width,height


    