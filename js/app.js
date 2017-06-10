import React, { Component } from 'react';
import ReactDOM from 'react-dom';
import Pusher from 'pusher-js';

const BASE_URL = "http://127.0.0.1:5000";

const SUITS = {
  DIAMONDS: "DIAMONDS",
  SPADES: "SPADES",
  CLUBS: "CLUBS",
  HEARTS: "HEARTS"
}

const CARDS = [
  "A",
  "2",
  "3",
  "4",
  "5",
  "6",
  "7",
  "8",
  "9",
  "10",
  "J",
  "Q",
  "K"
]

const STAGE = {
  PREFLOP: "PREFLOP",
  FLOP: "FLOP",
  TURN: "TURN",
  RIVER: "RIVER"
}

class App extends Component {
  constructor() {
    super();
    this.shuffle();

    // This binding is necessary to make `this` work in the callback
    this.deal = this.deal.bind(this);
    this.login = this.login.bind(this);
  }

  componentWillMount() {
    this.pusher = new Pusher('b62d17064a726aa724fe', {
      cluster: 'us2',
      encrypted: true
    });
  }

  componentDidMount() {
    this.channel.bind('start', function(message) {
      console.log(message);
    }, this);
  }

  login(username, password) {
    const body = {
      username: username,
      password: password,
      chip: chip
    };
    
    fetch(BASE_URL + "/login", {method: 'POST', body: body})
    .then(res => res.json())
    .then(data => {
      this.setState({
        user: {username: data.username, chip: data.chip},
        table: data.tableId
      });
    });

    this.channel = this.pusher.subscribe(data.tableId);
    this.channel.bind('action', function(message) {
      console.log(message);
    }, this);
  }

  join(seat) {
    const body = {
      tableId: this.state.tableId,
      seat: 0
    };
    fetch(BASE_URL + "/join", {method: 'POST', body: body})
    .then(res => res.json())
    .then(data => {
      this.channel = this.pusher.subscribe(data.tableId + data.seatId);
      this.channel.bind('action', function(message) {
        console.log(message);
      }, this);
    });
  }

  bet(amount) {
    fetch(BASE_URL + "/bet",{method: 'POST', body: {amount: ammount}})
    .then(res => res.json())
    .then(data => {

    });
  }

  render() {
    return (
      <div className="App">
        <div className="App-header">
          <h2>Welcome to AWESOME POKER!</h2>
        </div>
        <div className="App-intro">
          <Table cards={this.state.board} />
          <Player cards={this.state.hand} />
          <button onClick={this.deal}> DEAL </button>
        </div>
        {!this.state.user && <LoginDialog login={this.login} />}
      </div>
    );
  }
}

class LoginDialog extends Component {
  constructor(props) {
    super(props);
    this.props.username = "";
    this.props.password = "";
    this.submit = this.submit.bind(this);
  }

  submit() {
    this.props.login(this.props.username, this.props.password);
  }

  render() {
    return (
      <form class="loginDialog" onSubmit={submit}>
        <label>username: </label>
        <input type="text" name="username" value={this.props.username} />
        <label>password: </label>
        <input type="text" name="password" value={this.props.password} />
        <input type="submit" value="Submit" />
      </form>
    );
  }
}

class Table extends Component {
  render() {
    const cards = this.props.cards.map((card, index) =>
      <li key={index}>{card.suit + " " + card.value} </li>
    );
    return (
      <ul>
        <li>Board</li>
        {cards}
      </ul>
    )
  }
}

class Player extends Component {
  render() {
    const cards = this.props.cards.map((card, index) =>
      <li key={index}>{card.suit + " " + card.value} </li>
    );
    return (
      <ul>
        <li>HAND</li>
        {cards}
      </ul>
    )
  }
}

ReactDOM.render(<App />, document.getElementById('content'));
