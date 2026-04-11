'use strict';

const { Contract } = require('fabric-contract-api');

class Auth extends Contract {
  async putPp(ctx, data) {
    await ctx.stub.putState('pp', Buffer.from(data));
    return data;
  }

  async getPp(ctx) {
    return this._get(ctx, 'pp');
  }

  async putCh(ctx, dom, url, hct) {
    const val = JSON.stringify({ dom, url, hct });
    await ctx.stub.putState(`ch:${dom}`, Buffer.from(val));
    return val;
  }

  async getCh(ctx, dom) {
    return this._get(ctx, `ch:${dom}`);
  }

  async putRq(ctx, dom, sig, sid) {
    const uniqKey = `rqu:${sid}`;
    const old = await ctx.stub.getState(uniqKey);
    if (old && old.length) {
      throw new Error('sid already exists');
    }
    const val = JSON.stringify({ dom, sig, sid });
    await ctx.stub.putState(uniqKey, Buffer.from(dom));
    await ctx.stub.putState(`rq:${dom}:${sid}`, Buffer.from(val));
    return val;
  }

  async getRq(ctx, dom) {
    const out = [];
    const prefix = `rq:${dom}:`;
    const end = `${prefix}\uffff`;
    const iter = await ctx.stub.getStateByRange(prefix, end);
    try {
      while (true) {
        const item = await iter.next();
        if (item.done) {
          break;
        }
        const value = item.value && item.value.value;
        if (!value || !value.length) {
          continue;
        }
        out.push(JSON.parse(value.toString()));
      }
    } finally {
      await iter.close();
    }
    out.sort((a, b) => String(a.sid).localeCompare(String(b.sid)));
    return JSON.stringify(out);
  }

  async putRs(ctx, sid, res) {
    const val = JSON.stringify({ sid, res });
    await ctx.stub.putState(`rs:${sid}`, Buffer.from(val));
    return val;
  }

  async getRs(ctx, sid) {
    return this._get(ctx, `rs:${sid}`);
  }

  async _get(ctx, key) {
    const buf = await ctx.stub.getState(key);
    if (!buf || !buf.length) {
      return '';
    }
    return buf.toString();
  }

  async _getJson(ctx, key, fallback) {
    const text = await this._get(ctx, key);
    return text ? JSON.parse(text) : fallback;
  }
}

module.exports = Auth;
module.exports.contracts = [Auth];
