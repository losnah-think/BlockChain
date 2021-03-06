#-*-coding:utf-8
import socket
import Blockchain
import json
import ast
import db_test
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request ,render_template


UDP_PORT = [5001,5002,5003]

chain = Blockchain.Blockchain()
app = Flask(__name__)

node_identifier = str(uuid4()).replace('-', '')

@app.route('/contents/genesis',methods=['POST'])
def register_genesisBlock():
    start = time()
    block = chain.genesis_block()
    db, cursor = db_test.db_connection.db_init()
    response = {    
        'index' : block['index'],
        'timestamp' : block['timestamp'],
        'proof' : block['proof'],
        'previous_hash': block['previous_hash'],
        'merkle_root' : block['merkle_root'],
        'transactions' : block['transactions']
    }
    end = time()
    run_time = end - start
    db_test.view_insert(db, cursor, block['index'],block['timestamp'],block['proof'],block['previous_hash'],block['merkle_root'],run_time)
    db_test.contents_insert(db,cursor,block['index'],block['transactions'])
    db_test.db_connection.db_close(db)
    return jsonify(response), 200
    
@app.route('/contents/new', methods=['POST'])
def new_contents():
    if port not in UDP_PORT:
        values = request.get_json()
        required = ['user_id', 'contents_title', 'contents_main']
        if not all(k in values for k in required):
            return 'Missing Values', 400
        msg_data = {'user_id' : values['user_id'], 'contents_title' : values['contents_title'], 'contents_main' : values['contents_main']}     
        index = chain.new_contents(values['user_id'],values['contents_title'],values['contents_main'])
        MESSAGE = json.dumps(msg_data).encode()
        n_port = len(UDP_PORT)
        sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        for i in range(n_port):
            sock.sendto(MESSAGE, ('127.0.0.1',UDP_PORT[i]))
    else:
        recv_sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        recv_sock.bind(('127.0.0.1',port))
        data, addr = recv_sock.recvfrom(1024)
        print(addr)
        dict_b = json.loads(data)
        print(dict_b)
        print(type(dict_b))
        index = chain.new_contents(dict_b['user_id'],dict_b['contents_title'],dict_b['contents_main'])
        
    response = { 'message' : f'Transaction will be added to Block {index}'}
    return jsonify(response), 201

@app.route('/contents/upload', methods = ['POST'])
def upload():
    start = time()
    last_block = chain.last_block
    last_proof = last_block['proof']
    proof = chain.proof_of_work(last_proof)
    previous_hash = chain.hash(last_block)
    block = chain.new_block(proof, previous_hash)
    end = time()
    run_time = end - start
    db, cursor = db_test.db_connection.db_init()
    response = {    
        'index' : block['index'],
        'timestamp' : block['timestamp'],
        'proof' : block['proof'],
        'previous_hash': block['previous_hash'],
        'merkle_root' : block['merkle_root'],
        'transactions' : block['transactions']
    }
    db_test.view_insert(db, cursor, response['index'],response['timestamp'],response['proof'],response['previous_hash'],response['merkle_root'],run_time)
    db_test.contents_insert(db,cursor,response['index'],response['transactions'])
    db_test.db_connection.db_close(db)
    return jsonify(response), 200

@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain' : chain.chain,
        'length' : len(chain.chain),
    }

    return jsonify(response),200

@app.route('/nodes/register', methods=['POST'])
def register_node():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        chain.register_node(node)

    response = {
        'message' : 'New nodes have been added',
        'total_nodes' : list(chain.nodes)
    }
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = chain.resolve_conflicts()

    if replaced:
        response ={
            'message' : 'Chain is replaced',
            'new_chain' : chain.chain
        }
    else:
        response ={
            'message' : 'authoritative',
            'new_chain' : chain.chain
        }

    return jsonify(response), 200


if __name__=="__main__":
    from argparse import ArgumentParser
    
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port
    app.run(host='0.0.0.0', port=port)